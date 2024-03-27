# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""
from pathlib import Path
from osgeo import gdal
from typing import Any, Dict, Tuple, Iterator, List
from shapely import wkt
from threedigrid.admin.gridadmin import GridH5Admin
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from qgis.PyQt.QtCore import QVariant
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterLayer,
    QgsWkbTypes,
)

from threedi_results_analysis.processing.deps.discharge.leak_detector import LeakDetector
from threedi_results_analysis.processing.deps.discharge.discharge_reduction import LeakDetectorWithDischargeThreshold
from threedi_results_analysis.utils.threedi_result_aggregation.aggregation_classes import Aggregation, AggregationSign
from threedi_results_analysis.utils.threedi_result_aggregation.constants import AGGREGATION_VARIABLES, AGGREGATION_METHODS

Q_NET_SUM = Aggregation(
    variable=AGGREGATION_VARIABLES.get_by_short_name("q"),
    method=AGGREGATION_METHODS.get_by_short_name("sum"),
    sign=AggregationSign("net", "Net"),
)

STYLE_DIR = Path(__file__).parent / "styles"

QVARIANT_PYTHON_TYPES = {
    QVariant.Int: int,
    QVariant.Double: float
}


class DetectLeakingObstaclesBase(QgsProcessingAlgorithm):
    """
    Base algorithm for 'Detect leaking obstacles' algorithms, not to be exposed to users
    """

    INPUT_GRIDADMIN = "INPUT_GRIDADMIN"
    INPUT_DEM = "INPUT_DEM"
    INPUT_FLOWLINES = "INPUT_FLOWLINES"
    INPUT_OBSTACLES = "INPUT_OBSTACLES"
    INPUT_MIN_OBSTACLE_HEIGHT = "INPUT_MIN_OBSTACLE_HEIGHT"

    OUTPUT_EDGES = "OUTPUT_EDGES"
    OUTPUT_OBSTACLES = "OUTPUT_OBSTACLES"

    def initAlgorithm(self, config):

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_GRIDADMIN, "Gridadmin file", extension="h5"
            )
        )

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_DEM, "Digital Elevation Model"
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_OBSTACLES,
                "Linear obstacles",
                [QgsProcessing.TypeVectorLine],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT_FLOWLINES,
                "Flowlines",
                [QgsProcessing.TypeVectorLine],
                optional=True
            )
        )

        min_obstacle_height_param = QgsProcessingParameterNumber(
            self.INPUT_MIN_OBSTACLE_HEIGHT,
            "Minimum obstacle height (m)",
            type=QgsProcessingParameterNumber.Double
        )
        min_obstacle_height_param.setMetadata({"widget_wrapper": {"decimals": 3}})
        self.addParameter(min_obstacle_height_param)

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_EDGES,
                "Output: Obstacle on cell edge",
                type=QgsProcessing.TypeVectorLine
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_OBSTACLES,
                "Output: Obstacle in DEM",
                type=QgsProcessing.TypeVectorLine
            )
        )

    def checkParameterValues(self, parameters: Dict[str, Any], context: QgsProcessingContext) -> Tuple[bool, str]:
        success, msg = super().checkParameterValues(parameters, context)
        if success:
            msg_list = list()

            # check if min_obstacle_height > 0
            min_obstacle_height = self.parameterAsDouble(parameters, self.INPUT_MIN_OBSTACLE_HEIGHT, context)
            if min_obstacle_height <= 0:
                msg_list.append('Minimum obstacle height must be greater than 0')

            # check input obstacles has a field called crest_level
            input_obstacles_source = self.parameterAsSource(parameters, self.INPUT_OBSTACLES, context)
            if input_obstacles_source:
                if 'crest_level' not in input_obstacles_source.fields().names():
                    msg_list.append('Obstacle lines layer does not contain crest_level field')
            success = len(msg_list) == 0
            msg = '; '.join(msg_list)
        return success, msg

    @staticmethod
    def sink_field_data() -> List[Dict]:
        """
        Return a list of dicts that contain the data needed to defined fields in the feature sinks (output layers).
        Each dict contains the name (str) and the type (QVariant)
        """
        return [
            {"name": "flowline_id", "type": QVariant.Int},
            {"name": "exchange_level", "type": QVariant.Double},
            {"name": "crest_level", "type": QVariant.Double}
        ]

    def read_parameters(self, parameters, context, feedback):
        self.gridadmin_fn = self.parameterAsFile(parameters, self.INPUT_GRIDADMIN, context)
        self.gridadmin = GridH5Admin(self.gridadmin_fn)
        dem = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)
        dem_fn = dem.dataProvider().dataSourceUri()
        self.dem_ds = gdal.Open(dem_fn)
        flowlines_source = self.parameterAsSource(parameters, self.INPUT_FLOWLINES, context)
        obstacles_source = self.parameterAsSource(parameters, self.INPUT_OBSTACLES, context)
        self.min_obstacle_height = self.parameterAsDouble(parameters, self.INPUT_MIN_OBSTACLE_HEIGHT, context)

        crs = QgsCoordinateReferenceSystem(f"EPSG:{self.gridadmin.epsg_code}")

        self.sink_fields = QgsFields()
        for field_data in self.sink_field_data():
            self.sink_fields.append(QgsField(**field_data))

        self.edges_sink, self.edges_sink_dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT_EDGES,
            context,
            fields=self.sink_fields,
            geometryType=QgsWkbTypes.LineString,
            crs=crs
        )
        self.obstacles_sink, self.obstacles_sink_dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT_OBSTACLES,
            context,
            fields=self.sink_fields,
            geometryType=QgsWkbTypes.LineString,
            crs=crs
        )

        # get list of flowline ids
        if flowlines_source:
            field_index = flowlines_source.fields().indexFromName('id')
            self.flowline_ids = [feature.attributes()[field_index] for feature in flowlines_source.getFeatures()]
        else:
            self.flowline_ids = list(self.gridadmin.lines.id)

        if obstacles_source:
            feedback.setProgressText("Read linear obstacles input...")
            if obstacles_source.sourceCrs() != crs:
                raise QgsProcessingException(
                    "Obstacles input has different Coordinate Reference System than the gridadmin file"
                )
            crest_level_field_idx = obstacles_source.fields().indexFromName("crest_level")

            self.input_obstacles = list()
            for input_obstacle in obstacles_source.getFeatures():
                geom = wkt.loads(input_obstacle.geometry().asWkt())
                crest_level = float(input_obstacle[crest_level_field_idx])
                self.input_obstacles.append((geom, crest_level))
        else:
            self.input_obstacles = None

    def get_leak_detector(self, feedback):
        leak_detector = LeakDetector(
            gridadmin=self.gridadmin,
            dem=self.dem_ds,
            flowline_ids=self.flowline_ids,
            min_obstacle_height=self.min_obstacle_height,
            obstacles=self.input_obstacles,
            feedback=feedback
        )
        return leak_detector

    def processAlgorithm(self, parameters, context, feedback):
        self.read_parameters(parameters, context, feedback)
        feedback.setProgressText("Read computational grid...")
        leak_detector = self.get_leak_detector(feedback)
        if feedback.isCanceled():
            return {}
        feedback.setProgressText("Find obstacles...")
        leak_detector.run(feedback=feedback)
        feedback.setProgressText("Create 'Obstacle on cell edge' features...")
        self.add_features_to_sink(
            feedback=feedback,
            sink=self.edges_sink,
            features_data=leak_detector.results(geometry='EDGE')
        )
        feedback.setProgressText("Create 'Obstacle in DEM' features...")
        self.add_features_to_sink(
            feedback=feedback,
            sink=self.obstacles_sink,
            features_data=leak_detector.results(geometry='OBSTACLE')
        )

        return {
            self.OUTPUT_EDGES: self.edges_sink_dest_id,
            self.OUTPUT_OBSTACLES: self.obstacles_sink_dest_id
        }

    def group(self):
        return "Computational Grid"

    def groupId(self):
        return "computational_grid"


class DetectLeakingObstaclesAlgorithm(DetectLeakingObstaclesBase):
    """
    Detect obstacle lines in the DEM that are ignored by 3Di due to its location relative to cell edges
    """
    def postProcessAlgorithm(self, context, feedback):
        """Set styling of output vector layers"""
        edges_layer = context.getMapLayer(self.edges_sink_dest_id)
        edges_layer.loadNamedStyle(str(STYLE_DIR / "obstacle_on_cell_edge.qml"))

        obstacles_layer = context.getMapLayer(self.obstacles_sink_dest_id)
        obstacles_layer.loadNamedStyle(str(STYLE_DIR / "obstacle_in_dem.qml"))

        return {
            self.OUTPUT_EDGES: self.edges_sink_dest_id,
            self.OUTPUT_OBSTACLES: self.obstacles_sink_dest_id
        }

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm
        """
        return "detect_leaking_obstacles"

    def displayName(self):
        """
        Returns the algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "Detect leaking obstacles in DEM"

    def shortHelpString(self):
        return """
                <h3>Introduction</h3>
                <p>The elevation at which flow between 2D cells is possible (the 'exchange level'), depends on the elevation of the pixels directly adjacent to the cell edge. Obstacles in the DEM that do not cover the entire edge will therefore not stop the flow, i.e. water 'leaks' through the obstacle. This is more likely to occur if obstacles are diagonal and/or narrow compared to the computational grid size.</p>
                <p>This processing algorithm detects such cases. Please inspect the locations where the algorithm identifies leaking obstacles and add grid refinement and/or obstacles to the schematisation to solve the issue if needed.</p>
                <h3>Parameters</h3>
                <h4>Gridadmin file</h4>
                <p>HDF5-file (*.h5) containing a 3Di computational grid. Note that gridadmin files generated on the server contain exchange levels for 2D flowlines, whereas locally generated gridadmin files do not. In the latter case, the processing algorithm will analyse the DEM to obtain these values.</p>
                <h4>Digital elevation model</h4>
                <p>Raster of the schematisation's digital elevation model (DEM).</p>
                <h4>Linear obstacles</h4>
                <p>Obstacles in this layer will be used to update cell edge exchange levels, <i>in addition to</i> any obstacles already present in the gridadmin file (i.e. in files that were downloaded from the server). This input must be a vector layer with line geometry and a <i>crest_level</i> field</p>
                <h4>Flowlines</h4>
                <p>Can be used to limit the analysis to a specific part of the computational grid. For example, select flowlines that have a total discharge of > 10 m<sup>3</sup></p>
                <h4>Minimum obstacle height (m)</h4>
                <p>Only obstacles with a crest level that is significantly higher than the exchange level will be identified. 'Significantly higher' is defined as <em>crest level &gt; exchange level + minimum obstacle height</em>.</p>
                <h4>Vertical search precision (m)</h4>
                <p>The crest level of the identified obstacle will always be within <em>vertical search precision</em> of the actual crest level. A smaller value will yield more precise results; a higher value will make the algorithm faster to execute.</p>
                <h3>Outputs</h3>
                <h4>Obstacle in DEM&nbsp;</h4>
                <p>Approximate location of the obstacle in the DEM. Its geometry is a straight line between the highest pixels of the obstacle on the cell edges. Attributes:</p>
                <ul>
                <li> id: id of the flowline this obstacle affects. If more than one flowline is affected, the flowline with the lowest exchange level is used. </li>
                <li> crest_level: lowest elevation at which water can flow over the obstacle </li>
                <li> exchange_level: lowest exchange level of the cell edge(s) that this obstacle applies to </li>
                </ul>
                <p>The styling is shows the difference between the crest level and the exchange level</p>
                <h4>Obstacle on cell edge</h4>
                <p>Suggested obstacle to add to the schematisation. In most cases, it is recommended solve any leaking obstacle issues with grid refinement, and only add obstacles if this does not solve the issue.</p>
                <p>The styling shows the difference between the crest level and the exchange level</p>
            """

    def createInstance(self):
        return DetectLeakingObstaclesAlgorithm()


class DetectLeakingObstaclesWithDischargeThresholdAlgorithm(DetectLeakingObstaclesAlgorithm):
    INPUT_RESULTS_THREEDI = "INPUT_RESULTS_THREEDI"
    INPUT_MIN_DISCHARGE = "INPUT_MIN_DISCHARGE"

    def initAlgorithm(self, config):
        super().initAlgorithm(config)
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_RESULTS_THREEDI, "3Di Results file", extension="nc"
            )
        )

        min_discharge_param = QgsProcessingParameterNumber(
            self.INPUT_MIN_DISCHARGE,
            "Minimum cumulative discharge (m3)",
            type=QgsProcessingParameterNumber.Double
        )
        min_discharge_param.setMetadata({"widget_wrapper": {"decimals": 3}})
        self.addParameter(min_discharge_param)

    def sink_field_data(self):
        return super().sink_field_data() + [
            {"name": "discharge_without_obstacle", "type": QVariant.Double},
            {"name": "discharge_with_obstacle", "type": QVariant.Double},
            {"name": "discharge_reduction", "type": QVariant.Double}
        ]

    def read_parameters(self, parameters, context, feedback):
        super().read_parameters(parameters, context, feedback)
        self.min_discharge = self.parameterAsDouble(parameters, self.INPUT_MIN_DISCHARGE, context)
        self.results_threedi_fn = self.parameterAsFile(parameters, self.INPUT_RESULTS_THREEDI, context)
        self.grid_result_admin = GridH5ResultAdmin(self.gridadmin_fn, self.results_threedi_fn)

    def get_leak_detector(self, feedback):
        leak_detector = LeakDetectorWithDischargeThreshold(
            grid_result_admin=self.grid_result_admin,
            dem=self.dem_ds,
            flowline_ids=self.flowline_ids,
            min_obstacle_height=self.min_obstacle_height,
            min_discharge=self.min_discharge,
            obstacles=self.input_obstacles,
            feedback=feedback
        )
        return leak_detector

    def add_features_to_sink(self, feedback, sink: QgsFeatureSink, features_data: Iterator):
        for i, feature_data in enumerate(features_data):
            if feedback.isCanceled():
                return {}
            feature = QgsFeature()
            feature.setFields(self.sink_fields)
            for i, field in enumerate(self.sink_field_data()):
                convert = QVARIANT_PYTHON_TYPES[field["type"]]
                feature.setAttribute(i, convert(feature_data[field["name"]]))
            geometry = QgsGeometry()
            geometry.fromWkb(feature_data["geometry"].wkb)
            feature.setGeometry(geometry)
            sink.addFeature(feature, QgsFeatureSink.FastInsert)

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm
        """
        return "detect_leaking_obstacles_q_threshold"

    def displayName(self):
        """
        Returns the algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return "Detect leaking obstacles in DEM (discharge threshold)"

    def createInstance(self):
        return DetectLeakingObstaclesWithDischargeThresholdAlgorithm()
