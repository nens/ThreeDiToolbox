from datetime import datetime
from pathlib import Path
import tempfile

import pytest

from threedi_results_analysis.processing.deps.rasters_to_netcdf.rasters_to_netcdf import rasters_to_netcdf
from osgeo import gdal
gdal.UseExceptions()

DATA_DIR = Path(__file__).parent


def test_rasters_to_netcdf():
    filepaths = [
        DATA_DIR / "rain.tif",
        DATA_DIR / "rain.tif",
        DATA_DIR / "rain.tif"
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "output4.nc"
        rasters_to_netcdf(
            rasters=filepaths,
            start_time=datetime.strptime('2020-01-01T12:00:00', "%Y-%m-%dT%H:%M:%S"),
            interval=3600,
            units="mm",
            output_path=output_path
        )
        result_nc = gdal.Open(str(output_path))
        assert result_nc.RasterCount == 3
