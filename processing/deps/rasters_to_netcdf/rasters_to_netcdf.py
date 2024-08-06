from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Union, Dict

from cftime import date2num
import numpy as np
# import netCDF4
from osgeo import gdal, osr  # IMPORT THIS BEFORE IMPORTING h5netcdf!!!
import h5netcdf.legacyapi as netCDF4
from h5netcdf.legacyapi import Variable as h5netcdf_Variable
from pyproj import CRS

gdal.UseExceptions()
osr.UseExceptions()


def get_datasets(filepaths: List[Union[str, Path]]) -> List[gdal.Dataset]:
    result = list()
    for filepath in filepaths:
        dataset = gdal.Open(str(filepath))
        if not dataset:
            raise Exception(f"Unable to open {filepath}")
        result.append(dataset)
    return result


def get_srs(dataset: gdal.Dataset) -> osr.SpatialReference:
    projection = dataset.GetProjection()
    srs = osr.SpatialReference()
    srs.ImportFromWkt(projection)
    return srs


def rasters_have_same_srs(datasets: List[gdal.Dataset]) -> bool:
    if not datasets:
        raise ValueError("The filepaths list is empty.")

    base_crs = get_srs(datasets[0])

    for dataset in datasets[1:]:
        current_crs = get_srs(dataset)
        if not base_crs.IsSame(current_crs):
            return False
    return True


def rasters_have_same_geotransform(datasets: List[gdal.Dataset]) -> bool:
    if not datasets:
        raise ValueError("The filepaths list is empty.")

    base_geotransform = datasets[0].GetGeoTransform()

    for dataset in datasets[1:]:
        current_geotransform = dataset.GetGeoTransform()
        if base_geotransform != current_geotransform:
            return False
    return True


def rasters_have_same_dimensions(datasets: List[gdal.Dataset]):
    if not datasets:
        raise ValueError("The filepaths list is empty.")

    base_dimensions = datasets[0].RasterXSize, datasets[0].RasterYSize

    for dataset in datasets[1:]:
        current_dimensions = dataset.RasterXSize, dataset.RasterYSize
        if base_dimensions != current_dimensions:
            return False
    return True


def rasters_have_same_nodatavalue(datasets: List[gdal.Dataset]):
    if not datasets:
        raise ValueError("The filepaths list is empty.")

    base_ndv = datasets[0].GetRasterBand(1).GetNoDataValue()

    for dataset in datasets[1:]:
        current_ndv = dataset.GetRasterBand(1).GetNoDataValue()
        if base_ndv != current_ndv:
            return False
    return True


def setncatts(variable: h5netcdf_Variable, attributes: Dict):
    """Reproduces the behaviour of netcdf4.Variable.setncatts(), which is not supported in h5netcdf lecagy API"""
    for key, value in attributes.items():
        variable.setncattr(key, value)


def rasters_to_netcdf(
        rasters: List[Union[str, Path]],
        start_time: datetime,
        interval: int,
        units: str,
        output_path: Union[str, Path],
        time_units: str = 'seconds since 1970-01-01 00:00:00.0 +0000',
        calendar: str = 'standard',
        offset: int = 0
) -> None:
    """
    :param interval: interval in seconds
    :param units: one of 'mm', 'm/s', 'mm/h', 'mm/hr'. Note: in case of `mm` the rate is determined by looking at the
       next `time` value.
    :param offset: offset in seconds
    """
    datasets = get_datasets(rasters)
    assert rasters_have_same_srs(datasets), "Not all input rasters have the same Spatial Reference System"
    assert rasters_have_same_geotransform(datasets), "Not all input rasters have the same origin, pixel size, and skew"
    assert rasters_have_same_dimensions(datasets), "Not all input rasters have the same width and height"
    assert rasters_have_same_nodatavalue(datasets), "Not all input rasters have the same nodatavalue"

    srs = get_srs(datasets[0])
    crs = CRS.from_wkt(srs.ExportToWkt())
    geotransform = datasets[0].GetGeoTransform()

    # create netcdf
    output_dataset = netCDF4.Dataset(
        str(output_path),
        mode='w',
        # format="NETCDF4"
    )

    # dataset attributes
    output_dataset.setncattr(name='OFFSET', value=offset)
    crs_var = output_dataset.createVariable(varname='crs', datatype='int')
    setncatts(crs_var, crs.to_cf())
    crs_var.setncattr(name="spatial_ref", value=crs.to_wkt())
    crs_var.setncattr(name="GeoTransform", value=" ".join([str(i) for i in geotransform]))

    # set dimensions
    output_dataset.createDimension('lon', size=datasets[0].RasterXSize)
    output_dataset.createDimension('lat', size=datasets[0].RasterYSize)
    output_dataset.createDimension('time', size=len(rasters))

    # x and y or lon and lat
    x_attrs, y_attrs = crs.cs_to_cf()

    max_x_ordinate = geotransform[0] + datasets[0].RasterXSize * geotransform[1]
    x_ordinates = np.arange(
        start=geotransform[0],
        stop=max_x_ordinate - 0.5 * geotransform[1],  # to prevent unexpected behaviour due to rounding differences
        step=geotransform[1]
    )
    lon_var = output_dataset.createVariable(varname='lon', datatype='float32', dimensions=('lon',))
    lon_var[:] = x_ordinates
    setncatts(lon_var, x_attrs)

    max_y_ordinate = geotransform[3] + datasets[0].RasterYSize * geotransform[5]
    y_ordinates = np.arange(
        start=geotransform[3],
        stop=max_y_ordinate - 0.5 * geotransform[5],  # to prevent unexpected behaviour due to rounding differences
        step=geotransform[5]
    )
    lat_var = output_dataset.createVariable(varname='lat', datatype='float32', dimensions=('lat',))
    lat_var[:] = y_ordinates
    setncatts(lat_var, y_attrs)

    # time
    time_var = output_dataset.createVariable(varname='time', datatype='float64', dimensions=('time',))
    time_attrs = {
        'standard_name': 'time',
        'long_name': 'Time',
        'units': time_units,
        'calendar': calendar,
        'axis': 'T'
    }
    setncatts(time_var, time_attrs)
    time_delta = timedelta(seconds=interval)
    end_time = start_time + len(rasters) * time_delta
    time_steps_numpy = np.arange(start_time, end_time, time_delta, dtype='datetime64[s]')
    time_steps_datetime = [datetime.utcfromtimestamp(dt.astype('int')) for dt in time_steps_numpy]
    time_var[:] = date2num(time_steps_datetime, units=time_units, calendar=calendar)

    # rain data
    rain_var = output_dataset.createVariable(varname='values', datatype='float', dimensions=('time', 'lat', 'lon'))
    rain_attrs = {
        'long_name': 'rain',
        'grid_mapping': 'crs',
        '_FillValue': datasets[0].GetRasterBand(1).GetNoDataValue(),
        'missing_value': datasets[0].GetRasterBand(1).GetNoDataValue(),
        'units': units
    }
    setncatts(rain_var, rain_attrs)
    for i, dataset in enumerate(datasets):
        rain_var[i] = dataset.GetRasterBand(1).ReadAsArray()
        output_dataset.sync()
    output_dataset.close()

