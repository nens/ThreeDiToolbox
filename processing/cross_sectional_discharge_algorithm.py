# -*- coding: utf-8 -*-

"""
/***************************************************************************
 CrossSectionalDischargeAlgorithm
                                 A QGIS plugin
 Calculates net total discharge over a gauge line
                              -------------------
        begin                : 2022-04-18
        copyright            : (C) 2022 by Nelen en Schuurmans
        email                : leendert.vanwolfswinkel@nelen-schuurmans.nl
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = "Nelen en Schuurmans"
__date__ = "2022-04-18"
__copyright__ = "(C) 2022 by Nelen en Schuurmans"

# This will get replaced with a git SHA1 when you do a git archive
__revision__ = "$Format:%H$"
import numpy as np
import os
from pathlib import Path

from osgeo import ogr
from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsFeatureSink
from qgis.core import QgsField
from qgis.core import QgsFields
from qgis.core import QgsMarkerSymbol
from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsProperty
from qgis.core import QgsSymbolLayer
from qgis.core import QgsVectorLayer
from qgis.core import QgsVectorLayerSimpleLabeling
from qgis.core import QgsWkbTypes
from qgis.core import QgsGeometry
from qgis.core import QgsFeature
from qgis.PyQt.QtCore import QCoreApplication, QVariant
from shapely import wkt
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from threedigrid.admin.constants import TYPE_V2_CHANNEL
from threedigrid.admin.constants import TYPE_V2_CULVERT
from threedigrid.admin.constants import TYPE_V2_PIPE
from threedigrid.admin.constants import TYPE_V2_ORIFICE
from threedigrid.admin.constants import TYPE_V2_WEIR

from threedi_results_analysis.processing.deps.discharge.cross_sectional_discharge import left_to_right_discharge_ogr

MEMORY_DRIVER = ogr.GetDriverByName("MEMORY")
STYLE_DIR = Path(__file__).parent / "styles"


def ogr_feature_as_qgis_feature(
    ogr_feature, qgs_vector_lyr, tgt_wkb_type=None, tgt_fields=None
):

    # geometry
    ogr_geom_ref = ogr_feature.GetGeometryRef()
    if tgt_wkb_type is None:
        tgt_wkb_type = qgs_vector_lyr.wkbType()
    if not QgsWkbTypes.hasZ(tgt_wkb_type):
        ogr_geom_ref.FlattenTo2D()
    ogr_geom_wkb = ogr_geom_ref.ExportToWkb()
    qgs_geom = QgsGeometry()
    qgs_geom.fromWkb(ogr_geom_wkb)

    # attributes
    attributes = []
    if tgt_fields is None:
        tgt_fields = qgs_vector_lyr.fields()
    for field in tgt_fields:
        ogr_field_idx = ogr_feature.GetFieldIndex(field.name())
        if ogr_field_idx != -1:
            ogr_field_value = ogr_feature.GetField(ogr_field_idx)
            attributes.append(ogr_field_value)

    qgs_feature = QgsFeature()
    qgs_feature.setGeometry(qgs_geom)
    qgs_feature.setAttributes(attributes)
    return qgs_feature


class CrossSectionalDischargeAlgorithm(QgsProcessingAlgorithm):
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    GRIDADMIN_INPUT = "GRIDADMIN_INPUT"
    RESULTS_3DI_INPUT = "RESULTS_3DI_INPUT"
    CROSS_SECTION_LINES_INPUT = "CROSS_SECTION_LINES_INPUT"
    START_TIME = "START_TIME"
    END_TIME = "END_TIME"
    SUBSET = "SUBSET"
    INCLUDE_TYPES_1D = "INCLUDE_TYPES_1D"
    FIELD_NAME_INPUT = "FIELD_NAME_INPUT"
    OUTPUT_CROSS_SECTION_LINES = "OUTPUT_CROSS_SECTION_LINES"
    OUTPUT_FLOWLINES = "OUTPUT_FLOWLINES"
    OUTPUT_TIME_SERIES = "OUTPUT_TIME_SERIES"

    # These are not algorithm parameters:
    SUBSET_NAMES = ["2D Surface flow", "2D Groundwater flow", "1D flow"]
    SUBSETS = ["2D_OPEN_WATER", "2D_GROUNDWATER", "1D"]

    TYPES_1D_NAMES = ["Channel", "Culvert", "Pipe", "Orifice", "Weir"]
    TYPES_1D = [
        TYPE_V2_CHANNEL,
        TYPE_V2_CULVERT,
        TYPE_V2_PIPE,
        TYPE_V2_ORIFICE,
        TYPE_V2_WEIR,
    ]

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        self.addParameter(
            QgsProcessingParameterFile(
                self.GRIDADMIN_INPUT, self.tr("Gridadmin file"), extension="h5"
            )
        )
        self.addParameter(
            QgsProcessingParameterFile(
                self.RESULTS_3DI_INPUT,
                self.tr("Results 3Di file"),
                extension="nc",
            )
        )

        self.addParameter(
            QgsProcessingParameterVectorLayer(
                self.CROSS_SECTION_LINES_INPUT,
                self.tr("Cross-section lines"),
                [QgsProcessing.TypeVectorLine],
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_TIME,
                "Start time (s)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.END_TIME,
                "End time (s)",
                type=QgsProcessingParameterNumber.Integer,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.SUBSET, "Subset", options=self.SUBSET_NAMES, optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.INCLUDE_TYPES_1D,
                "1D Flowline types to include",
                options=self.TYPES_1D_NAMES,
                allowMultiple=True,
                defaultValue=list(range(len(self.TYPES_1D))),  # all enabled
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.FIELD_NAME_INPUT,
                self.tr("Output field name"),
                defaultValue="q_net_sum",
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_FLOWLINES,
                self.tr("Output: Intersected flowlines"),
                type=QgsProcessing.TypeVectorLine,
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_TIME_SERIES,
                self.tr("Output: Timeseries"),
                fileFilter="*.csv",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        gridadmin_fn = self.parameterAsFile(
            parameters, self.GRIDADMIN_INPUT, context
        )
        results_3di_fn = self.parameterAsFile(
            parameters, self.RESULTS_3DI_INPUT, context
        )
        gr = GridH5ResultAdmin(gridadmin_fn, results_3di_fn)
        cross_section_lines = self.parameterAsVectorLayer(
            parameters, self.CROSS_SECTION_LINES_INPUT, context
        )
        self.cross_section_lines_id = cross_section_lines.id()
        start_time = (
            self.parameterAsInt(parameters, self.START_TIME, context)
            if parameters[self.START_TIME] is not None
            else None
        )  # use `is not None` to handle `== 0` properly
        end_time = (
            self.parameterAsInt(parameters, self.END_TIME, context)
            if parameters[self.END_TIME] is not None
            else None
        )  # use `is not None` to handle `== 0` properly
        subset = (
            self.SUBSETS[parameters[self.SUBSET]]
            if parameters[self.SUBSET] is not None
            else None
        )  # use `is not None` to handle `== 0` properly
        feedback.pushInfo(f"Using subset: {subset}")
        content_types = [
            self.TYPES_1D[i] for i in parameters[self.INCLUDE_TYPES_1D]
        ]
        feedback.pushInfo(f"Using content_types: {content_types}")
        self.field_name = self.parameterAsString(
            parameters, self.FIELD_NAME_INPUT, context
        )
        self.csv_output_file_path = self.parameterAsFileOutput(
            parameters, self.OUTPUT_TIME_SERIES, context
        )
        self.csv_output_file_path = (
            f"{os.path.splitext(self.csv_output_file_path)[0]}.csv"
        )

        flowlines_sink_fields = QgsFields()
        flowlines_sink_fields.append(QgsField(name="id", type=QVariant.Int))
        flowlines_sink_fields.append(
            QgsField(name="source_table_id", type=QVariant.Int)
        )
        flowlines_sink_fields.append(
            QgsField(name="source_table", type=QVariant.String)
        )
        flowlines_sink_fields.append(
            QgsField(name="line_type", type=QVariant.Int)
        )
        flowlines_sink_fields.append(
            QgsField(name="gauge_line_id", type=QVariant.Int)
        )
        flowlines_sink_fields.append(
            QgsField(name="q_net_sum", type=QVariant.Double)
        )

        crs = QgsCoordinateReferenceSystem(f"EPSG:{gr.epsg_code}")
        (flowlines_sink, self.flowlines_sink_dest_id) = self.parameterAsSink(
            parameters,
            self.OUTPUT_FLOWLINES,
            context,
            fields=flowlines_sink_fields,
            geometryType=QgsWkbTypes.LineString,
            crs=crs,
        )

        self.target_field_idx = (
            cross_section_lines.dataProvider().fieldNameIndex(self.field_name)
        )
        if self.target_field_idx == -1:
            attribute = QgsField(
                name=self.field_name, type=QVariant.Double, len=16, prec=3
            )
            cross_section_lines.dataProvider().addAttributes([attribute])
            cross_section_lines.updateFields()
            self.target_field_idx = (
                cross_section_lines.dataProvider().fieldNameIndex(
                    self.field_name
                )
            )

        feedback.setProgress(0)
        self.total_discharges = dict()
        if cross_section_lines.selectedFeatureCount() > 0:
            iterator = cross_section_lines.getSelectedFeatures()
            nr_features = cross_section_lines.selectedFeatureCount()
        else:
            iterator = cross_section_lines.getFeatures()
            nr_features = cross_section_lines.featureCount()
        for i, gauge_line in enumerate(iterator):
            if feedback.isCanceled():
                return {}
            feedback.setProgressText(
                f"Processing cross-section line {gauge_line.id()}..."
            )
            shapely_linestring = wkt.loads(gauge_line.geometry().asWkt())
            tgt_ds = MEMORY_DRIVER.CreateDataSource("")
            ts_gauge_line, total_discharge = left_to_right_discharge_ogr(
                gr=gr,
                gauge_line=shapely_linestring,
                tgt_ds=tgt_ds,
                gauge_line_id=gauge_line.id(),
                start_time=start_time,
                end_time=end_time,
                subset=subset,
                content_types=content_types,
            )
            feedback.pushInfo(
                f"Net sum of discharge for cross-section line {gauge_line.id()}: {total_discharge}"
            )
            if i == 0:
                ts_all_cross_section_lines = ts_gauge_line
                column_names = ['"timestep"', f'"{gauge_line.id()}"']
                formatting = ["%d", "%.6f"]
            else:
                ts_all_cross_section_lines = np.column_stack(
                    [ts_all_cross_section_lines, ts_gauge_line[:, 1]]
                )
                column_names.append(f'"{gauge_line.id()}"')
                formatting.append("%.6f")
            self.total_discharges[
                gauge_line.id()
            ] = total_discharge  # update attr vals in postprocessing (main thread)
            ogr_layer = tgt_ds.GetLayerByName("flowline")
            for ogr_feature in ogr_layer:
                qgs_feature = ogr_feature_as_qgis_feature(
                    ogr_feature,
                    flowlines_sink,
                    tgt_wkb_type=QgsWkbTypes.LineString,
                    tgt_fields=flowlines_sink_fields,
                )
                flowlines_sink.addFeature(
                    qgs_feature, QgsFeatureSink.FastInsert
                )
            feedback.setProgress(100 * i / nr_features)

        np.savetxt(
            self.csv_output_file_path,
            ts_all_cross_section_lines,
            delimiter=",",
            header=",".join(column_names),
            fmt=formatting,
            comments="",
        )
        layer = QgsVectorLayer(self.csv_output_file_path, "Time series output")
        context.temporaryLayerStore().addMapLayer(layer)
        layer_details = QgsProcessingContext.LayerDetails(
            "Output: Time series", context.project(), "Output: Time series"
        )
        context.addLayerToLoadOnCompletion(layer.id(), layer_details)

        return {
            self.OUTPUT_FLOWLINES: self.flowlines_sink_dest_id,
            self.OUTPUT_TIME_SERIES: self.csv_output_file_path,
        }

    def postProcessAlgorithm(self, context, feedback):
        """Set styling of output vector layers"""
        cross_section_lines = context.getMapLayer(self.cross_section_lines_id)

        # update attr vals in postprocessing (main thread)
        cross_section_lines.startEditing()
        for fid, total_discharge in self.total_discharges.items():
            cross_section_lines.changeAttributeValue(
                fid, self.target_field_idx, float(total_discharge)
            )
        cross_section_lines.commitChanges()

        cross_section_lines.loadNamedStyle(
            str(STYLE_DIR / "cross_sectional_discharge.qml")
        )

        # set label
        label_settings = cross_section_lines.labeling().settings()
        label_settings.fieldName = f"round(abs({self.field_name})) || ' m³'"
        labelling = QgsVectorLayerSimpleLabeling(label_settings)
        cross_section_lines.setLabeling(labelling)

        # set arrow rotation
        rotation_expression = f'if( "{self.field_name}" < 0, 0, 180)'
        data_defined_angle = (
            QgsMarkerSymbol()
            .dataDefinedAngle()
            .fromExpression(rotation_expression)
        )
        cross_section_lines.renderer().symbol()[
            0
        ].subSymbol().setDataDefinedAngle(data_defined_angle)

        # make arrow invisible if attribute value for field self.field_name is NULL
        enable_symbol_layer = QgsProperty.fromExpression(
            f'"{self.field_name}" is not null'
        )
        cross_section_lines.renderer().symbol()[0].setDataDefinedProperty(
            QgsSymbolLayer.PropertyLayerEnabled, enable_symbol_layer
        )
        context.project().addMapLayer(cross_section_lines)

        flowlines_output_layer = context.getMapLayer(
            self.flowlines_sink_dest_id
        )
        flowlines_output_layer.loadNamedStyle(
            str(STYLE_DIR / "cross_sectional_discharge_flowlines.qml")
        )

        return {
            self.OUTPUT_FLOWLINES: self.flowlines_sink_dest_id,
            self.OUTPUT_TIME_SERIES: self.csv_output_file_path,
        }

    def name(self):
        return "crosssectionaldischarge"

    def displayName(self):
        return self.tr("Cross-sectional discharge")

    def group(self):
        return self.tr("Post-process results")

    def groupId(self):
        return "postprocessing"

    def shortHelpString(self):
        return self.tr(
            """
            <h3>Calculate total net discharge over a cross-section line.</h3>
            <p>The result will be written to a field specified by <i>output field name</i>. This field will be created if it does not exist.</p>
            <p>The sign (positive/negative) of the output values depends on the drawing direction of the cross-section line. Positive values indicate flow from the left-hand side of the cross-section line to the right-hand side. Negative values indicate flow from right to left.</p>
            <h3>Parameters</h3>
            <h4>Gridadmin file</h4>
            <p>HDF5 file (*.h5) containing the computational grid of a 3Di model</p>
            <h4>Results 3Di file</h4>
            <p>NetCDF (*.nc) containing the results of a 3Di simulation</p>
            <h4>Cross-section lines</h4>
            <p>Lines for which to calculate the total net discharge passing that line</p>
            <h4>Start time</h4>
            <p>If specified, all data before <i>start time</i> will be excluded. Units: seconds since start of simulation.</p>
            <h4>End time</h4>
            <p>If specified, all data after <i>end time</i> will be excluded. Units: seconds since start of simulation.</p>
            <h4>Subset</h4>
            <p>Limit the analysis to flowlines in a specific flow domain.</p>
            <h4>1D Flowline types to include</h4>
            <p>Further filtering of specific 1D flowlines. This setting does not affect 2D or 1D/2D flowlines.</p>
            <h4>Output field name</h4>
            <p>Name of the field in the <i>cross-section lines</i> layer to which total net discharge will be written.</p>
            <h3>Outputs</h3>
            <h4>Total net discharge per cross-section line</h4>
            <p>This result will be written to the <i>cross-section lines</i> layer, in a field specified by <i>output field name</i>. This field will be created if it does not exist.</p>
            <h4>Intersected flowlines</h4>
            <p>Flowlines that are included in the analysis. The styling will indicate if there is positive (left-hand side to right-hand side of the cross-section line) or negative net flow through each of these flowlines.<p>
            <h4>Time series</h4>
            <p>Table (CSV file) with time series of net flow over each cross-section line. Tip: use the DataPlotly QGIS plugin to visualize these time series.</p>
            """
        )

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return CrossSectionalDischargeAlgorithm()
