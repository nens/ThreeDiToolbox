from collections import OrderedDict
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
)
from threedi_results_analysis.processing.processing_utils import gridadmin2geopackage, load_computational_layers


class ThreeDiConvertToGpkgAlgorithm(QgsProcessingAlgorithm):
    """Convert gridadmin.h5 to GeoPackage with vector layers and add subset of those layers to the map canvas."""

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    LAYERS_TO_ADD = OrderedDict()

    def flags(self):
        return super().flags() | QgsProcessingAlgorithm.FlagNoThreading

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ThreeDiConvertToGpkgAlgorithm()

    def name(self):
        return "threedi_convert_gridadmin_to_gpkg"

    def displayName(self):
        return self.tr("Computational grid from gridadmin.h5 file")

    def group(self):
        return self.tr("Computational Grid")

    def groupId(self):
        return "computational_grid"

    def shortHelpString(self):
        return self.tr("Create computational grid from gridadmin.h5 file")

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, self.tr("Gridadmin.h5 file"), extension="h5",
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, self.tr("Output GeoPackage file"), fileFilter="*.gpkg",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        input_gridadmin = self.parameterAsString(parameters, self.INPUT, context)
        if input_gridadmin is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        gpkg_path = self.parameterAsFileOutput(parameters, self.OUTPUT, context)
        if gpkg_path is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.OUTPUT))
        if gpkg_path.endswith(".file"):
            gpkg_path = gpkg_path.rsplit(".", 1)[0] + ".gpkg"

        gpkg_layers = gridadmin2geopackage(input_gridadmin, gpkg_path, context, feedback)
        self.LAYERS_TO_ADD.update(gpkg_layers)

        return {}

    def postProcessAlgorithm(self, context, feedback):
        project = context.project()
        load_computational_layers(self.LAYERS_TO_ADD, project)
        self.LAYERS_TO_ADD.clear()
        return {}
