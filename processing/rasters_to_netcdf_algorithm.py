from typing import List

from threedi_results_analysis.processing.deps.rasters_to_netcdf.rasters_to_netcdf import rasters_to_netcdf
from qgis.core import (
    QgsMapLayer,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsRasterLayer,
)


class RastersToNetCDFAlgorithm(QgsProcessingAlgorithm):
    """
    Base algorithm for 'Detect leaking obstacles' algorithms, not to be exposed to users
    """

    INPUT_RASTERS = "INPUT_RASTERS"
    INPUT_START_TIME = "INPUT_START_TIME"
    INPUT_INTERVAL = "INPUT_INTERVAL"
    INPUT_UNITS = "INPUT_UNITS"
    INPUT_OUTPUT_PATH = "INPUT_OUTPUT_PATH"
    INPUT_OFFSET = "INPUT_OFFSET"

    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterMultipleLayers(
                name=self.INPUT_RASTERS,
                description="Input rasters",
                layerType=QgsProcessing.TypeRaster,
            )
        )

        self.addParameter(
            QgsProcessingParameterDateTime(
                name=self.INPUT_START_TIME,
                description="Start",
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.INPUT_INTERVAL,
                description="Interval [s]",
                type=QgsProcessingParameterNumber.Integer
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                name=self.INPUT_OFFSET,
                description="Offset [s]",
                type=QgsProcessingParameterNumber.Integer,
                defaultValue=0
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.INPUT_UNITS,
                description="Units",
                options=["mm", "m/s", "mm/h", "mm/hr"]
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                name=self.INPUT_OUTPUT_PATH,
                description="Output file",
                fileFilter=".nc"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_raster_layers: List[QgsMapLayer] = self.parameterAsLayerList(parameters, self.INPUT_RASTERS, context)
        rasters = [layer.dataProvider().dataSourceUri() for layer in input_raster_layers]
        start_datetime = self.parameterAsDateTime(parameters, self.INPUT_START_TIME, context) \
            .toPyDateTime() \
            .replace(second=0, microsecond=0)
        interval = self.parameterAsInt(parameters, self.INPUT_INTERVAL, context)
        offset = self.parameterAsInt(parameters, self.INPUT_OFFSET, context)
        units = self.parameterAsEnumString(parameters, self.INPUT_UNITS, context)
        output_path = self.parameterAsFile(parameters, self.INPUT_OUTPUT_PATH, context)
        rasters_to_netcdf(
            rasters=rasters,
            start_time=start_datetime,
            interval=interval,
            units=units,
            output_path=output_path,
            offset=offset
        )

        layer = QgsRasterLayer(output_path, "Spatiotemporal NetCDF")
        context.temporaryLayerStore().addMapLayer(layer)
        layer_details = QgsProcessingContext.LayerDetails(
            "Spatiotemporal NetCDF",
            context.project(),
            self.OUTPUT
        )
        context.addLayerToLoadOnCompletion(
            layer.id(),
            layer_details
        )

        return {
            self.OUTPUT: output_path,
        }

    def group(self):
        return "Pre-process simulation inputs"

    def groupId(self):
        return "pre_process_sim_inputs"

    def shortHelpString(self):
        return """
                <p>Create a NetCDF file with data of rain or other forcings that vary in space and time.</p>
                <p>The algorithm takes a list of rasters and stacks them into a NetCDF, one raster for each time step.</p>
                <p>ⓘ Note that 3Di also offers services that seamlessly integrate historical and forecast rain with 3Di. For example, to set up flood early warning systems or operational water management systems. Get in touch via www.3diwatermanagement.com to learn the possibilities for your area.</p>
                <h3>Parameters</h3>
                <h4>Input rasters</h4>
                <p>A list of rasters (e.g. GeoTIFF) to be stacked.</p>
                <h4>Start</h4>
                <p>Date and time of the first time step in the output NetCDF.</p>
                <h4>Interval</h4>
                <p>Time in seconds between time steps.</p>
                <h4>Offset</h4>
                <p>If greater than 0, the forcing will only be applied after this number of seconds has passed in the simulation.</p>
                <h4>Units</h4>
                <p><The units of the forcing's data./p>
                <h4>Output file</h4>
                <p>Name and location of the NetCDF output. Must have the .nc extension.</p>
        """

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm
        """
        return "rasters_to_netcdf"

    def displayName(self):
        """
        Returns the algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "Rasters to spatiotemporal NetCDF"

    def createInstance(self):
        return RastersToNetCDFAlgorithm()
