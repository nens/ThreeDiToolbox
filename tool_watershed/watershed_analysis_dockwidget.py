# -*- coding: utf-8 -*-
# TODO Analyzed target nodes behouden bij afsluiten plugin
# TODO analyzed target nodes leegmaken bij clear ouputs

# TODO: If source is polygon layer, transfer polygon id to result layers
# TODO mogelijkheid om van een pand op te vragen wat het downstream effect is

# TODO: Allow save and loading of result sets to a single geopackage incl. styling

# TODO: auto-Enable/disable buttons in Target Nodes and Outputs sections

# TODO: add sub-categories to result flowline styling
# TODO: add discharge (q net sum) attribute to result flowlines
# TODO: add flow direction styling to result flowlines
import os
import pathlib
import processing
import numpy as np
import logging
from typing import Iterable, List
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, Qt, QVariant
from qgis.core import (
    Qgis,
    QgsApplication,
    QgsTask,
    QgsMessageLog,
    QgsProject,
    QgsDataSourceUri,
    QgsFeatureRequest,
    QgsExpression,
    QgsFeature,
    QgsGeometry,
    QgsProcessingFeedback,
    QgsMapLayerProxyModel,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsField,
    QgsVectorLayer,
)
from qgis.gui import QgsMapToolIdentify, QgsVertexMarker
from osgeo import ogr, osr
from threedigrid.admin.gridresultadmin import GridH5ResultAdmin
from .watershed_analysis_networkx import Graph3Di
from threedi_results_analysis.utils.threedi_result_aggregation.threedigrid_ogr import threedigrid_to_ogr
from threedi_results_analysis.utils.ogr2qgis import as_qgis_memory_layer, append_to_qgs_vector_layer
from .smoothing import polygon_gaussian_smooth
from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem
from threedi_results_analysis.utils.qprojects import set_read_only

logger = logging.getLogger(__name__)

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), "watershed_analysis_dockwidget_base.ui"))

STYLE_DIR = os.path.join(os.path.dirname(__file__), "style")
MEMORY_DRIVER = ogr.GetDriverByName("MEMORY")
DEFAULT_THRESHOLD = 1
MESSAGE_CATEGORY = "Watershed Analysis"
ATTRIBUTE_NAME = "watershed_result_sets"
GROUP_NAME = "Watershed tool outputs"


class FindImperviousSurfaceError(Exception):
    """Raised when something goes wrong when finding impervious surfaces"""
    pass


def bbox_of_features(features: List):
    """Returns None if empty list is given as input"""
    first_pass = True
    bbox = None
    for feat in features:
        if first_pass:
            bbox = feat.geometry().boundingBox()
            first_pass = False
        else:
            bbox.combineExtentWith(feat.geometry().boundingBox())
    return bbox


class Graph3DiQgsConnector:
    """Connect a Graph3Di and its inputs and outputs to a QGIS Project"""

    # TODO: class alles laten erven van Graph3Di en evt. nieuw object met alle QGIS-dingen
    result_cell_attr_types = {
        "id": ogr.OFTInteger,
        "node_type": ogr.OFTInteger,
        "location": ogr.OFTString,
        "catchment_id": ogr.OFTInteger,
        "from_polygon": ogr.OFTInteger,
    }

    result_flowline_attr_types = {
        "id": ogr.OFTInteger,
        "content_type": ogr.OFTString,
        "kcu": ogr.OFTInteger,
        "kcu_description": ogr.OFTString,
        "location": ogr.OFTString,
        "catchment_id": ogr.OFTInteger,
        "from_polygon": ogr.OFTInteger,
        "exchange_level": ogr.OFTReal,
    }

    def __init__(self, result_item: ThreeDiResultItem, model, parent_dock, preloaded_layers):
        """Constructor."""
        self._filter = None
        self.parent_dock = parent_dock
        self.iface = parent_dock.iface
        self.graph_3di = Graph3Di(subset=None)
        self._sqlite = None

        self.model = model
        self.result_id = None  # Id of result_item refering to netcdf/gridadmin
        if result_item:
            self.result_id = result_item.id

        self.result_group = None
        self.target_node_layer = None
        self.result_markers = []

        self.preloaded_layers = preloaded_layers

        self.result_cell_layer = None
        self.result_flowline_layer = None
        self.result_catchment_layer = None
        self.impervious_surface_layer = None

        self.result_sets = []
        self.dissolved_result_sets = []
        self.smooth_result_catchments = []
        self._result_markers = []

    @property
    def gr(self):
        return self.graph_3di.gr

    @gr.setter
    def gr(self, value):
        # ! Do not use any QObject that lives on the main thread here, because this setter is called from a QgsTask
        # See https://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/tasks.html
        self.graph_3di.gr = value

    @property
    def sqlite(self):
        return self._sqlite

    @sqlite.setter
    def sqlite(self, sqlite):
        sqlite_pathlib_path = pathlib.Path(sqlite)
        if not isinstance(sqlite_pathlib_path, pathlib.PurePath):
            raise TypeError
        value_changed = sqlite != self._sqlite
        self._sqlite = sqlite_pathlib_path
        if value_changed:
            if self.impervious_surface_layer is None and self._sqlite is not None:
                self.create_impervious_surface_layer()

    @property
    def threshold(self):
        return self.graph_3di.threshold

    @threshold.setter
    def threshold(self, value):
        self.graph_3di.threshold = value

    @property
    def start_time(self):
        return self.graph_3di.start_time

    @start_time.setter
    def start_time(self, value):
        self.graph_3di.start_time = value

    @property
    def end_time(self):
        return self.graph_3di.end_time

    @end_time.setter
    def end_time(self, value):
        self.graph_3di.end_time = value

    @property
    def filter(self):
        return self._filter

    @filter.setter
    def filter(self, ids: List):
        if isinstance(ids, list):
            for id_i in ids:
                if not isinstance(id_i, int):
                    raise TypeError("Filter must be set to None or list of int")
            self._filter = ids.copy()
        elif ids is None:
            self._filter = None
        else:
            raise TypeError("Filter must be set to None or list of int")
        self.update_layer_filters()

    def average_cell_size(self, result_set_id):
        request = QgsFeatureRequest()
        request.setFilterExpression(f"catchment_id = {result_set_id}")
        features = self.result_cell_layer.getFeatures(request)
        count = 0
        area = 0
        for feat in features:
            count += 1
            area += feat.geometry().area()
        if area > 0:
            return area / count
        else:
            return None

    def update_layer_filters(self):
        filtered_ids = set(self.result_sets) & set(self.filter if self.filter is not None else self.result_sets)
        filtered_ids_str = ",".join(map(str, filtered_ids))
        if self.filter is None:
            subset_string = ""
        else:
            subset_string = "catchment_id IN ({})".format(filtered_ids_str)
        # filter to leave subset_string out if empty
        flowline_subset_string = " AND ".join(filter(None, [subset_string, "kcu != 100"]))
        self.result_catchment_layer.setSubsetString(subset_string)
        self.result_cell_layer.setSubsetString(subset_string)
        self.result_flowline_layer.setSubsetString(flowline_subset_string)
        if self.impervious_surface_layer is not None:
            self.impervious_surface_layer.setSubsetString(subset_string)

    def new_result_set_id(self):
        if len(self.result_sets) == 0:
            self.result_sets.append(1)  # 1-based index because this is common in GIS id fields
        else:
            self.result_sets.append(max(self.result_sets) + 1)
        return max(self.result_sets)

    def gr_updated(self):
        """Executed when a new 3Di result is selected (self.gr is changed)"""
        if isinstance(self.graph_3di.gr, GridH5ResultAdmin):

            # prepare caching of result item layers
            if self.result_id not in self.preloaded_layers:
                self.preloaded_layers[self.result_id] = {}

            self.prepare_result_layer_group()
            # Note: the sequence is deliberate; the target nodes are below the result layers because otherwise, if \
            # zoomed out too much, the target nodes will cover the result.
            self.prepare_target_node_layer()

            self.prepare_result_cell_layer()
            self.prepare_result_flowline_layer()
            self.prepare_catchment_layer()

    def add_to_layer_tree_group(self, layer):
        """
        Add a layer to the 3Di Network Analysis layer tree group
        """
        project = QgsProject.instance()
        project.addMapLayer(layer, addToLegend=False)
        self.result_group.insertLayer(0, layer)

    def prepare_result_layer_group(self):
        assert self.result_id

        # Check if group is cached
        if "group" in self.preloaded_layers[self.result_id]:
            logger.info("Retrieving result group from cache")
            self.result_group = self.preloaded_layers[self.result_id]["group"]
        else:
            # We'll place the result layers in the grid group
            result = self.model.get_result(self.result_id)
            grid_item = result.parent()
            assert grid_item
            tool_group = grid_item.layer_group.findGroup(GROUP_NAME)
            if not tool_group:
                logger.info("Creating new group for watershed tool results.")
                tool_group = grid_item.layer_group.insertGroup(0, GROUP_NAME)
                tool_group.willRemoveChildren.connect(lambda n, i1, i2: self._group_removed(n, i1, i2))

            # Add result group
            self.result_group = tool_group.findGroup(result.text())
            if not self.result_group:
                self.result_group = tool_group.addGroup(result.text())

            # Use to modify result name when QgsLayerTreeNode is renamed. Note that this does not cause a
            # infinite signal loop because the model only emits the result_changed when the text has actually
            # changed.
            self.result_group.nameChanged.connect(lambda _, txt, result_item=result: result_item.setText(txt))

            # Cache
            self.preloaded_layers[self.result_id]["group"] = self.result_group

    def _group_removed(self, n, idxFrom, idxTo):
        for result_id in list(self.preloaded_layers):
            group = self.preloaded_layers[result_id]["group"]
            for i in range(idxFrom, idxTo+1):
                if n.children()[i] is group:
                    del self.preloaded_layers[result_id]["group"]

    def prepare_target_node_layer(self):
        # We'll use the node layer of the computational grid
        result = self.model.get_result(self.result_id)
        grid_item = result.parent()
        assert grid_item
        layer_id = grid_item.layer_ids["node"]
        self.target_node_layer = QgsProject.instance().mapLayer(layer_id)

        # Add additional result feature
        provider = self.target_node_layer.dataProvider()
        result_field = QgsField(ATTRIBUTE_NAME, QVariant.String)
        # Unable to set using default value using this, going to loop below..
        # default_value = QgsDefaultValue("''")
        # result_field.setDefaultValueDefinition(default_value)
        if (self.target_node_layer.fields().indexFromName(ATTRIBUTE_NAME) == -1):
            if not provider.addAttributes([result_field]):
                logger.error("Unable to add attributes, aborting...")
                return

            self.target_node_layer.updateFields()

        attr_idx = self.target_node_layer.fields().indexFromName(ATTRIBUTE_NAME)
        id_list = [f.id() for f in self.target_node_layer.getFeatures()]
        update_dict = {i: {attr_idx: ""} for i in id_list}
        if not provider.changeAttributeValues(update_dict):
            logger.error("Unable to set default values in 'result_set' attribute.")

    def clear_target_node_layer(self):
        """Empty the result_set field of all features in the target_node_layer"""
        if self.target_node_layer is not None:
            request = QgsFeatureRequest()
            request.setFilterExpression(f"{ATTRIBUTE_NAME} != ''")
            attr_idx = self.target_node_layer.fields().indexFromName(ATTRIBUTE_NAME)
            id_list = [f.id() for f in self.target_node_layer.getFeatures(request)]
            update_dict = {i: {attr_idx: ""} for i in id_list}
            if not self.target_node_layer.dataProvider().changeAttributeValues(update_dict):
                logger.error("Unable to set default values in 'result_set' attribute for clearing.")

            for marker in self._result_markers:
                self.iface.mapCanvas().scene().removeItem(marker)
            self._result_markers.clear()

            self.target_node_layer.triggerRepaint()

    def prepare_result_cell_layer(self):
        # Check whether this layer is cached.
        if "cell" in self.preloaded_layers[self.result_id]:
            logger.info("Retrieving result cell layer from cache")
            layer_id = self.preloaded_layers[self.result_id]["cell"]
            self.result_cell_layer = QgsProject.instance().mapLayer(layer_id)
            set_read_only(self.result_cell_layer, True)

    def update_analyzed_target_cells(self, target_node_ids, result_set):
        ids_str = ",".join(map(str, target_node_ids))
        request = QgsFeatureRequest()
        request.setFilterExpression(f"id IN ({ids_str})")
        idx = self.target_node_layer.fields().indexFromName(ATTRIBUTE_NAME)

        for feat in self.target_node_layer.getFeatures(request):
            old_result_sets = feat[ATTRIBUTE_NAME]
            old_result_sets = str(old_result_sets or '')
            result_sets_list = old_result_sets.split(",")
            result_sets_list.append(result_set)
            new_result_sets = ",".join(map(str, result_sets_list))
            if not self.target_node_layer.dataProvider().changeAttributeValues({feat.id(): {idx: new_result_sets}}):
                logger.error("Unable to update result sets")

            result_marker = QgsVertexMarker(self.iface.mapCanvas())
            result_marker.setIconType(QgsVertexMarker.ICON_BOX)
            result_marker.setColor(Qt.yellow)
            result_marker.setFillColor(Qt.black)
            result_marker.setPenWidth(3)
            result_marker.setCenter(feat.geometry().asPoint())
            self._result_markers.append(result_marker)

        self.target_node_layer.triggerRepaint()
        self.update_layer_filters()

    def append_result_cells(self, cell_ids, upstream: bool, result_set: int):
        cells = self.gr.cells.filter(id__in=list(cell_ids))

        nw_ids = list(cells.id)

        nw_catchment_ids = [result_set] * cells.count

        if upstream:
            location = ["upstream"] * cells.count
        else:
            location = ["downstream"] * cells.count

        from_polygon = [0] * cells.count

        attributes = {
            "id": nw_ids,
            "location": location,
            "catchment_id": nw_catchment_ids,
            "from_polygon": from_polygon,
        }

        ds = MEMORY_DRIVER.CreateDataSource("")
        threedigrid_to_ogr(
            threedigrid_src=cells, tgt_ds=ds, attributes=attributes, attr_data_types=self.result_cell_attr_types, include_all_threedigrid_attributes=True,
        )
        layer = ds.GetLayerByName("cell")
        if self.result_cell_layer:
            append_to_qgs_vector_layer(ogr_layer=layer, qgs_vector_layer=self.result_cell_layer)
        else:
            qgs_lyr_name = "Result cells"
            self.result_cell_layer = as_qgis_memory_layer(layer, qgs_lyr_name)
            self.add_to_layer_tree_group(self.result_cell_layer)
            qml = os.path.join(STYLE_DIR, "result_cells.qml")
            self.result_cell_layer.loadNamedStyle(qml)
            set_read_only(self.result_cell_layer, True)
            # cache
            self.preloaded_layers[self.result_id]["cell"] = self.result_cell_layer.id()

    def clear_result_cell_layer(self):
        """Remove all features from layer that contains the upstream and/or downstream cells"""
        if self.result_cell_layer is not None:
            self.result_cell_layer.dataProvider().truncate()

    def prepare_result_flowline_layer(self):
        # Check whether this layer is cached.
        if "flowline" in self.preloaded_layers[self.result_id]:
            logger.info("Retrieving result flowline layer from cache")
            layer_id = self.preloaded_layers[self.result_id]["flowline"]
            self.result_flowline_layer = QgsProject.instance().mapLayer(layer_id)
            set_read_only(self.result_flowline_layer, True)

    def find_flowlines(self, node_ids: List, upstream: bool, result_set: int):
        """Find flowlines that connect the input nodes \
        and append them to the result flowline layer"""
        flowlines_ids = self.graph_3di.flowlines_between_nodes(node_ids=node_ids)
        self.append_result_flowlines(flowline_ids=flowlines_ids, upstream=upstream, result_set=result_set)

    def append_result_flowlines(self, flowline_ids, upstream: bool, result_set: int):
        flowlines = self.gr.lines.filter(id__in=list(flowline_ids))
        nw_ids = list(flowlines.id)
        nw_catchment_ids = [result_set] * flowlines.count
        if upstream:
            location = ["upstream"] * flowlines.count
        else:
            location = ["downstream"] * flowlines.count
        from_polygon = [0] * flowlines.count
        content_type = [''] * flowlines.count
        attributes = {
            "id": nw_ids,
            "location": location,
            "catchment_id": nw_catchment_ids,
            "from_polygon": from_polygon,
            "content_type": content_type,
        }

        ds = MEMORY_DRIVER.CreateDataSource("")
        threedigrid_to_ogr(
            threedigrid_src=flowlines, tgt_ds=ds, attributes=attributes, attr_data_types=self.result_flowline_attr_types, include_all_threedigrid_attributes=True
        )
        layer = ds.GetLayerByName("flowline")
        if self.result_flowline_layer:
            append_to_qgs_vector_layer(ogr_layer=layer, qgs_vector_layer=self.result_flowline_layer)
        else:
            self.result_flowline_layer = as_qgis_memory_layer(layer, "Result flowlines (1D)")
            self.add_to_layer_tree_group(self.result_flowline_layer)
            self.result_flowline_layer.setSubsetString("kcu != 100")
            self.result_flowline_layer.loadNamedStyle(os.path.join(STYLE_DIR, "result_flowlines.qml"))
            set_read_only(self.result_flowline_layer, True)
            # cache
            self.preloaded_layers[self.result_id]["flowline"] = self.result_flowline_layer.id()

    def clear_result_flowline_layer(self):
        """Remove all features from layer that contains the upstream and/or downstream flowlines"""
        if self.result_flowline_layer is not None:
            self.result_flowline_layer.dataProvider().truncate()

    def prepare_catchment_layer(self):

        if "catchment" in self.preloaded_layers[self.result_id]:
            logger.info("Retrieving result catchment layer from cache")
            layer_id = self.preloaded_layers[self.result_id]["catchment"]
            self.result_catchment_layer = QgsProject.instance().mapLayer(layer_id)
        else:
            logger.info("Watershed: creating new catchment result layer.")
            ogr_driver = ogr.GetDriverByName("Memory")
            ogr_data_source = ogr_driver.CreateDataSource("")
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(int(self.graph_3di.gr.epsg_code))
            ogr_lyr = ogr_data_source.CreateLayer("", srs, geom_type=ogr.wkbPolygon)

            for fieldname, fieldtype in self.result_cell_attr_types.items():
                field = ogr.FieldDefn(fieldname, fieldtype)
                ogr_lyr.CreateField(field)

            qgs_lyr_name = "Result catchments"
            self.result_catchment_layer = as_qgis_memory_layer(ogr_lyr, qgs_lyr_name)
            self.add_to_layer_tree_group(self.result_catchment_layer)

            qml = os.path.join(STYLE_DIR, "result_catchments.qml")
            self.result_catchment_layer.loadNamedStyle(qml)

            self.preloaded_layers[self.result_id]["catchment"] = self.result_catchment_layer.id()

        set_read_only(self.result_catchment_layer, True)

    def clear_catchment_layer(self):
        """Remove all features from layer that contains the upstream and/or downstream cells"""
        if self.result_catchment_layer is not None:
            fids = [feat.id() for feat in self.result_catchment_layer.getFeatures()]
            self.result_catchment_layer.dataProvider().truncate()
            self.result_catchment_layer.featuresDeleted.emit(fids)

    def dissolve_cells(self):
        """Dissolve cells in self.result_cells_layer of all not yet dissolved result sets"""
        saved_subsetstring = self.result_cell_layer.subsetString()
        non_dissolved_ids = set(self.result_sets) - set(self.dissolved_result_sets)
        non_dissolved_ids_str = ",".join(map(str, non_dissolved_ids))
        subset_string = "catchment_id IN ({})".format(non_dissolved_ids_str)
        self.result_cell_layer.setSubsetString(subset_string)

        feedback = QgsProcessingFeedback()
        dslv_params = {
            "INPUT": self.result_cell_layer,  # QgsVectorLayer
            "FIELD": ["location", "catchment_id"],  # dissolve field (str)
            "OUTPUT": "memory:",
        }

        multipolys = processing.run("qgis:dissolve", dslv_params, feedback=feedback)["OUTPUT"]
        to_single_params = {"INPUT": multipolys, "OUTPUT": "memory:Result Catchments"}  # QgsVectorLayer
        nw_result_catchments_layer = processing.run("qgis:multiparttosingleparts", to_single_params, feedback=feedback)[
            "OUTPUT"
        ]

        self.result_catchment_layer.startEditing()
        # Catchment table now has different number of attributes
        # self.result_catchment_layer.dataProvider().addFeatures(nw_result_catchments_layer.getFeatures())
        new_features = []
        for orig_feature in nw_result_catchments_layer.getFeatures():
            new_feature = QgsFeature(self.result_catchment_layer.fields())
            new_feature["id"] = orig_feature["id"]
            new_feature["node_type"] = orig_feature["node_type"]
            new_feature["location"] = orig_feature["location"]
            new_feature["catchment_id"] = orig_feature["catchment_id"]
            new_feature["from_polygon"] = orig_feature["from_polygon"]
            new_feature.setGeometry(orig_feature.geometry())
            new_features.append(new_feature)

        success = self.result_catchment_layer.dataProvider().addFeatures(new_features)
        if not success:
            logger.error("Unable to add catchment features")
        self.result_catchment_layer.commitChanges()
        self.dissolved_result_sets = self.result_sets.copy()
        self.result_catchment_layer.triggerRepaint()
        self.result_cell_layer.setSubsetString(saved_subsetstring)
        self.result_catchment_layer.featureAdded.emit(self.result_catchment_layer.featureCount())

    def smooth_catchment_layer(self):
        saved_subsetstring = self.result_catchment_layer.subsetString()
        self.result_catchment_layer.setSubsetString("")
        self.result_catchment_layer.setReadOnly(False)
        self.result_catchment_layer.startEditing()
        for feature in self.result_catchment_layer.getFeatures():
            if feature.id() not in self.smooth_result_catchments:
                avg_cell_size = self.average_cell_size(feature["catchment_id"])
                avg_grid_space = np.sqrt(avg_cell_size)
                sigma = np.max([10, 16 * np.log(avg_grid_space) - 30])  # formula fitted to trial and error results
                sample_dist = np.max([2, 2 * np.log(avg_grid_space) - 3])
                geom = feature.geometry()
                ogr_geom = ogr.CreateGeometryFromWkb(geom.asWkb())
                ogr_geom_smooth = polygon_gaussian_smooth(ogr_geom, sigma=sigma, sample_dist=sample_dist)
                qgs_geom_smooth = QgsGeometry()
                qgs_geom_smooth.fromWkb(ogr_geom_smooth.ExportToWkb())
                self.result_catchment_layer.changeGeometry(feature.id(), qgs_geom_smooth)
            self.smooth_result_catchments.append(feature.id())
        if not self.result_catchment_layer.commitChanges():
            logger.error("Unable to commit changes after smoothing")
        self.result_catchment_layer.setReadOnly(True)
        self.result_catchment_layer.setSubsetString(saved_subsetstring)

    def create_impervious_surface_layer(self):
        # This layer is different from the other result layers, because it is a copy of an existing layer from the
        # spatialite; It is easier to copy the layer using the QGIS API
        self.impervious_surface_source_layer = QgsVectorLayer(
            path=str(self.sqlite) + "|layername=v2_impervious_surface",
            baseName="v2_impervious_surface",
            providerLib="ogr",
        )

        if "surface" in self.preloaded_layers[self.result_id]:
            logger.info("Retrieving impervious layer layer from cache")
            layer_id = self.preloaded_layers[self.result_id]["surface"]
            self.impervious_surface_layer = QgsProject.instance().mapLayer(layer_id)

            # We'll just use the plain layer, and we'll re-add all attributes below
            attribute_list = self.impervious_surface_layer.attributeList()
            self.impervious_surface_layer.dataProvider().deleteAttributes(attribute_list)
            self.impervious_surface_layer.updateFields()
        else:
            logger.info("Watershed: creating new impervious surface layer.")
            self.impervious_surface_layer = QgsVectorLayer("Polygon", "Impervious surface", "memory")
            qml = os.path.join(STYLE_DIR, "result_impervious_surfaces.qml")
            msg, result = self.impervious_surface_layer.loadNamedStyle(qml)
            if not result:
                logger.error(f"Unable to load styling {qml} for impervious layer: {msg}")
            self.add_to_layer_tree_group(self.impervious_surface_layer)
            self.preloaded_layers[self.result_id]["surface"] = self.impervious_surface_layer.id()

        fields = self.impervious_surface_source_layer.fields().toList()
        catchment_id_field = QgsField("catchment_id", QVariant.Int)
        fields.append(catchment_id_field)
        crs = QgsCoordinateReferenceSystem()
        crs.createFromId(4326)
        self.impervious_surface_layer.setCrs(crs)
        self.impervious_surface_layer.dataProvider().addAttributes(fields)
        self.impervious_surface_layer.updateFields()

        set_read_only(self.impervious_surface_layer, True)

    def append_impervious_surfaces(self, result_set: int, ids: List = None, expression: str = None):
        """
        Copy features from the source v2_impervious_surface table to the result table
        impervious surfaces may be selected by ids or by expression. Expression overrules ids
        """
        impervious_surface_layer_subset_string = self.impervious_surface_layer.subsetString()
        self.impervious_surface_layer.setSubsetString("")
        max_fid_before = self.impervious_surface_layer.dataProvider().featureCount()
        if expression is None:
            ids_str = ",".join(map(str, ids))
            expression = f"id IN ({ids_str})"
        self.impervious_surface_source_layer.setSubsetString(expression)
        features = self.impervious_surface_source_layer.getFeatures()
        success = self.impervious_surface_layer.dataProvider().addFeatures(features)
        if not success:
            return False
        request = QgsFeatureRequest(QgsExpression(f"$id > {max_fid_before}"))
        added_features = self.impervious_surface_layer.getFeatures(request)
        catchment_id_field_idx = self.impervious_surface_layer.dataProvider().fieldNameIndex("catchment_id")
        attr_map = {feat.id(): {catchment_id_field_idx: result_set} for feat in added_features}
        success = self.impervious_surface_layer.dataProvider().changeAttributeValues(attr_map)
        if not success:
            return False
        self.impervious_surface_layer.updateExtents()
        self.impervious_surface_layer.setSubsetString(impervious_surface_layer_subset_string)
        return True

    def clear_impervious_surface_layer(self):
        """
        Remove all features from layer
        """
        if self.impervious_surface_layer is not None:
            self.impervious_surface_layer.dataProvider().truncate()

    def find_impervious_surfaces(self, node_ids: List, result_set: int = None):
        """
        Find impervious surfaces connected to nodes and append them to the impervious surface layer
        """
        if self.impervious_surface_layer is not None and self.sqlite is not None:
            nodes = self.gr.nodes.filter(id__in=node_ids)
            connection_node_ids = set(nodes.content_pk) - {None, -9999}
            connection_node_ids_str = ",".join(map(str, connection_node_ids))
            expression = (
                "id in (SELECT impervious_surface_id FROM v2_impervious_surface_map "
                f"WHERE connection_node_id IN ({connection_node_ids_str}))"
            )
            success = self.append_impervious_surfaces(result_set=result_set, expression=expression)
            if not success:
                raise FindImperviousSurfaceError()

    def upstream_downstream_analysis(self, target_node_ids: Iterable, upstream: bool, downstream: bool, smoothing: bool):
        progress_message_bar = self.iface.messageBar().createMessage("3Di Network Analysis is being performed...")
        progress = QtWidgets.QProgressBar()
        current_progress = 0
        max_progress = 2
        if upstream:
            max_progress += 4
        if downstream:
            max_progress += 3

        # smoothing is optional as well
        if not smoothing:
            max_progress -= 1

        progress.setMaximum(max_progress)
        progress.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        progress_message_bar.layout().addWidget(progress)
        self.iface.messageBar().pushWidget(progress_message_bar, Qgis.Info)
        self.iface.mainWindow().repaint()  # to show the message before the task starts

        result_set = self.new_result_set_id()

        if upstream:
            upstream_node_ids = self.graph_3di.upstream_nodes(target_node_ids)
            # upstream_node_ids -= set(target_node_ids) # remove the target nodes from the result
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: upstream_node_ids identified")

            self.append_result_cells(cell_ids=upstream_node_ids, upstream=True, result_set=result_set)
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: upstream result cells appended")

            upstream_node_ids.update(set(target_node_ids))
            self.find_flowlines(node_ids=list(upstream_node_ids), upstream=True, result_set=result_set)
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: upstream flowlines found")

            try:
                self.find_impervious_surfaces(node_ids=list(upstream_node_ids), result_set=result_set)
            except FindImperviousSurfaceError:
                self.iface.messageBar().pushMessage(
                    MESSAGE_CATEGORY, "Something went wrong when finding impervious surfaces", Qgis.Warning
                )
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: impervious surfaces found")

        if downstream:
            downstream_node_ids = self.graph_3di.downstream_nodes(target_node_ids)
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: downstream_node_ids identified")

            # downstream_node_ids -= set(target_node_ids) # remove the target nodes from the result
            self.append_result_cells(cell_ids=downstream_node_ids, upstream=False, result_set=result_set)
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: downstream result cells appended")

            downstream_node_ids.update(set(target_node_ids))
            self.find_flowlines(node_ids=list(downstream_node_ids), upstream=False, result_set=result_set)
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: downstream flowlines found")

        self.dissolve_cells()
        current_progress += 1
        progress.setValue(current_progress)
        print(f"{current_progress}/{max_progress}: cells dissolved")

        if smoothing:
            self.smooth_catchment_layer()
            current_progress += 1
            progress.setValue(current_progress)
            print(f"{current_progress}/{max_progress}: catchments smoothed")

        self.result_cell_layer.triggerRepaint()
        self.result_flowline_layer.triggerRepaint()
        if self.impervious_surface_layer is not None:
            self.impervious_surface_layer.triggerRepaint()
        self.update_analyzed_target_cells(target_node_ids, result_set)
        current_progress += 1
        progress.setValue(current_progress)
        print(f"{current_progress}/{max_progress}: finished")

        self.iface.messageBar().clearWidgets()

    def zoom_to_results(self):
        # catchments
        # not needed, because bbox of catchments < bbox of cells

        project_crs = QgsProject.instance().crs()
        source_crs = QgsCoordinateReferenceSystem(f"EPSG:{int(self.graph_3di.gr.epsg_code)}")
        transform = QgsCoordinateTransform(source_crs, project_crs, QgsProject.instance())
        impervious_surface_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        impervious_surface_transform = QgsCoordinateTransform(
            impervious_surface_crs, project_crs, QgsProject.instance()
        )
        transformed_bbox = None

        # target nodes
        if self.target_node_layer is not None:
            request = QgsFeatureRequest(QgsExpression(f"{ATTRIBUTE_NAME} != ''"))
            features = self.target_node_layer.getFeatures(request)
            nodes_bbox = bbox_of_features(features=features)
            if nodes_bbox is not None:
                transformed_bbox = transform.transformBoundingBox(nodes_bbox)

        # cells
        if self.result_cell_layer is not None:
            features = self.result_cell_layer.getFeatures()
            cells_bbox = bbox_of_features(features=features)
            if cells_bbox is not None:
                transformed_cells_bbox = transform.transformBoundingBox(cells_bbox)
                if transformed_bbox is None:
                    transformed_bbox = transformed_cells_bbox
                elif transformed_cells_bbox is not None:
                    transformed_bbox.combineExtentWith(transformed_cells_bbox)

        # flowlines
        if self.result_flowline_layer is not None:
            features = self.result_flowline_layer.getFeatures()
            flowlines_bbox = bbox_of_features(features=features)
            if flowlines_bbox is not None:  # layer exists but no contains no features
                transformed_flowlines_bbox = transform.transformBoundingBox(flowlines_bbox)
                if transformed_bbox is None:
                    transformed_bbox = transformed_flowlines_bbox
                elif transformed_flowlines_bbox is not None:
                    transformed_bbox.combineExtentWith(transformed_flowlines_bbox)

        # impervious surfaces
        if self.impervious_surface_layer is not None:
            features = self.impervious_surface_layer.getFeatures()
            impervious_surface_bbox = bbox_of_features(features=features)
            if impervious_surface_bbox is not None:
                transformed_impervious_surface_bbox = impervious_surface_transform.transformBoundingBox(
                    impervious_surface_bbox
                )
                if transformed_bbox is None:
                    transformed_bbox = transformed_impervious_surface_bbox
                elif transformed_impervious_surface_bbox is not None:
                    transformed_bbox.combineExtentWith(transformed_impervious_surface_bbox)

        if transformed_bbox is not None:
            transformed_bbox.scale(1.1)
            self.iface.mapCanvas().setExtent(transformed_bbox)
        return

    def clear_all(self):
        self.clear_target_node_layer()
        self.clear_result_cell_layer()
        self.clear_result_flowline_layer()
        self.clear_catchment_layer()
        self.clear_impervious_surface_layer()
        self.result_sets = []
        self.iface.mapCanvas().refreshAllLayers()


class CatchmentMapTool(QgsMapToolIdentify):
    def __init__(self, iface, parent_button, gq: Graph3DiQgsConnector, upstream, downstream, smoothing):
        super().__init__(gq.iface.mapCanvas())
        self.gq = gq
        self.upstream = upstream
        self.downstream = downstream
        self.smoothing = smoothing
        self.iface = iface
        self.parent_button = parent_button
        self.set_cursor()

    @property
    def upstream(self):
        return self._upstream

    @upstream.setter
    def upstream(self, value):
        self._upstream = value

    @property
    def downstream(self):
        return self._downstream

    @downstream.setter
    def downstream(self, value):
        self._downstream = value

    def canvasReleaseEvent(self, event):
        x = event.pos().x()
        y = event.pos().y()

        identify_results = self.identify(x=int(x), y=int(y), layerList=[self.gq.target_node_layer])
        if len(identify_results) == 0:
            self.iface.messageBar().pushMessage(
                MESSAGE_CATEGORY, "Please click on a target node", level=Qgis.Info
            )
        else:
            target_node_id = identify_results[0].mFeature.id()
            self.gq.upstream_downstream_analysis(
                target_node_ids=[target_node_id], upstream=self.upstream, downstream=self.downstream, smoothing=self.smoothing
            )

    def activate(self):
        pass

    def deactivate(self):
        if self.parent_button is not None:
            self.parent_button.setChecked(False)

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return True

    def set_cursor(self):
        cursor = QtGui.QCursor()
        cursor.setShape(Qt.CrossCursor)
        self.canvas().setCursor(cursor)


class WatershedAnalystDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    closingWidget = pyqtSignal(object)  # ThreeDiGridItem or None

    def __init__(self, iface, model, preloaded_layers, parent=None):
        super(WatershedAnalystDockWidget, self).__init__(parent)

        self.iface = iface
        self.model = model
        self.catchment_map_tool = None
        self.tm = QgsApplication.taskManager()
        self.connect_gq(None, None)
        self.preloaded_layers = preloaded_layers
        self.setUpUI()

    def _populate_results(self) -> None:
        self.comboBoxResult.clear()
        for result in self.model.get_results(checked_only=False):
            self.comboBoxResult.addItem(f"{result.parent().text()} | {result.text()}", result.id)

    def select_result(self, index: int) -> None:
        result_id = self.comboBoxResult.itemData(index)
        result = self.model.get_result(result_id)
        results_3di = result.path
        gridadmin = result.parent().path.with_suffix('.h5')
        assert os.path.isfile(results_3di) and os.path.isfile(gridadmin)

        self.disconnect_gq()
        self.connect_gq(result, self.preloaded_layers)
        gr = GridH5ResultAdmin(str(gridadmin), str(results_3di))
        self.gq.end_time = int(gr.nodes.timestamps[-1])
        if self.doubleSpinBoxThreshold.value() is not None:
            self.gq.threshold = self.doubleSpinBoxThreshold.value()
        else:
            self.gq.threshold = DEFAULT_THRESHOLD
        update_gr_task = UpdateGridAdminTask(
            description="Preprocess 3Di Results for Network Analysis", parent=self, gr=gr
        )
        self.iface.messageBar().pushMessage(
            MESSAGE_CATEGORY, "Started pre-processing simulation results", Qgis.Info
        )
        self.tm.addTask(update_gr_task)
        self.iface.mainWindow().repaint()  # to show the message before the task starts

    def add_result(self, result_item: ThreeDiResultItem) -> None:
        currentIndex = self.comboBoxResult.currentIndex()
        self.comboBoxResult.addItem(f"{result_item.parent().text()} | {result_item.text()}", result_item.id)
        self.comboBoxResult.setCurrentIndex(currentIndex)

    def remove_result(self, result_item: ThreeDiResultItem):
        idx = self.comboBoxResult.findData(result_item.id)
        logger.info(f"Removing result {result_item.id} at index {idx}")
        assert idx != -1
        if idx == self.comboBoxResult.currentIndex():
            self.disconnect_gq()
            self.comboBoxResult.setCurrentIndex(-1)
            self.QgsFileWidgetSqlite.setEnabled(False)

        self.comboBoxResult.removeItem(idx)

    def change_result(self, result_item: ThreeDiResultItem):
        idx = self.comboBoxResult.findData(result_item.id)
        assert idx != -1
        self.comboBoxResult.setItemText(idx, f"{result_item.parent().text()} | {result_item.text()}")

    def closeEvent(self, event):
        QgsProject.instance().cleared.disconnect(self.close)

        result_id = self.gq.result_id if self.gq else None
        self.disconnect_gq()
        # Emit so other tools might reset styling
        if result_id:
            result = self.model.get_result(result_id)
            assert result
            self.closingWidget.emit(result.parent())
        else:
            self.closingWidget.emit(None)

        event.accept()

    def connect_gq(self, result_item: ThreeDiResultItem, preloaded_layers):
        self.gq = Graph3DiQgsConnector(result_item=result_item, model=self.model, parent_dock=self, preloaded_layers=preloaded_layers)
        self.gq.start_time = 0  # initial value of widget is 0, so valueChanged() signal will not be emitted when ...
        # ... a 3Di result is loaded for the first time

    def disconnect_gq(self):
        if not self.gq:
            return

        self.unset_map_tool()
        self.gq.clear_all()
        self.gq = None

    def sqlite_selected(self):
        uri = QgsDataSourceUri()
        uri.setDatabase(self.QgsFileWidgetSqlite.filePath())
        schema = ""
        table = "v2_impervious_surface"
        geom_column = "the_geom"
        uri.setDataSource(schema, table, geom_column)

        display_name = "just for validity"
        vlayer = QgsVectorLayer(uri.uri(), display_name, "spatialite")
        if vlayer.isValid():
            self.gq.sqlite = self.QgsFileWidgetSqlite.filePath()
            self.iface.messageBar().pushMessage(
                MESSAGE_CATEGORY, "Succesfully added impervious surfaces from model", level=Qgis.Success
            )
        else:
            self.iface.messageBar().pushMessage(
                MESSAGE_CATEGORY, "Invalid 3Di model sqlite selected", level=Qgis.Warning
            )
            self.QgsFileWidgetSqlite.setFilePath("")

    def threshold_changed(self):
        self.gq.threshold = self.doubleSpinBoxThreshold.value()

    def start_time_changed(self):
        self.gq.start_time = self.doubleSpinBoxStartTime.value()

    def end_time_changed(self):
        self.gq.end_time = self.doubleSpinBoxEndTime.value()

    def unset_map_tool(self):
        if self.catchment_map_tool is not None:
            self.iface.mapCanvas().unsetMapTool(self.catchment_map_tool)
            self.catchment_map_tool = None

    def pushbutton_click_on_canvas_clicked(self):
        if self.pushButtonClickOnCanvas.isChecked() and self.gq.graph_3di.isready:
            self.catchment_map_tool = CatchmentMapTool(
                self.iface,
                parent_button=self.pushButtonClickOnCanvas,
                gq=self.gq,
                upstream=self.checkBoxUpstream.isChecked(),
                downstream=self.checkBoxDownstream.isChecked(),
                smoothing=self.checkBoxSmoothing.isChecked(),
            )
            self.iface.mapCanvas().setMapTool(self.catchment_map_tool)
        else:
            self.unset_map_tool()

    def pushbutton_catchment_for_selected_nodes_clicked(self):
        selected_node_ids = []
        for feature in self.gq.target_node_layer.getSelectedFeatures():
            selected_node_ids.append(feature.id())

        if len(selected_node_ids) == 0:
            self.iface.messageBar().pushMessage(
                MESSAGE_CATEGORY, "Please first select one or more target nodes", level=Qgis.Warning
            )
        else:
            if self.gq.graph_3di.isready:
                self.gq.upstream_downstream_analysis(
                    target_node_ids=selected_node_ids,
                    upstream=self.checkBoxUpstream.isChecked(),
                    downstream=self.checkBoxDownstream.isChecked(),
                    smoothing=self.checkBoxSmoothing.isChecked(),
                )
            else:
                self.iface.messageBar().pushMessage(
                    MESSAGE_CATEGORY, "Please select 3Di results first", level=Qgis.Warning
                )

    def pushbutton_catchment_for_polygons_clicked(self):
        if self.gq.graph_3di.isready:
            polygon_lyr = self.mMapLayerComboBoxTargetPolygons.currentLayer()
            src_crs = polygon_lyr.crs()
            tgt_crs = QgsCoordinateReferenceSystem(f"EPSG:{self.gq.gr.epsg_code}")
            tr = QgsCoordinateTransform(src_crs, tgt_crs, QgsProject.instance())

            if self.checkBoxSelectedPolygonsOnly.isChecked():
                polygon_features = polygon_lyr.getSelectedFeatures()
            else:
                polygon_features = polygon_lyr.getFeatures()
            for feat in polygon_features:
                target_node_ids = []
                geom = feat.geometry()
                geom.transform(tr)
                req = QgsFeatureRequest(geom.boundingBox())  # for performance
                for point in self.gq.target_node_layer.getFeatures(req):
                    if geom.contains(point.geometry()):
                        target_node_ids.append(point.id())
                self.gq.upstream_downstream_analysis(
                    target_node_ids=target_node_ids,
                    upstream=self.checkBoxUpstream.isChecked(),
                    downstream=self.checkBoxDownstream.isChecked(),
                    smoothing=self.checkBoxSmoothing.isChecked(),
                )

    def pushbutton_clear_results_clicked(self):
        self.gq.clear_all()
        self.checkBoxBrowseResultSets.setEnabled(False)
        self.spinBoxBrowseResultSets.setValue(1)
        self.spinBoxBrowseResultSets.setMinimum(1)
        self.spinBoxBrowseResultSets.setMaximum(1)
        self.spinBoxBrowseResultSets.setEnabled(False)

    def checkbox_upstream_state_changed(self):
        if self.catchment_map_tool is not None:
            self.catchment_map_tool.upstream = self.checkBoxUpstream.isChecked()

    def checkbox_downstream_state_changed(self):
        if self.catchment_map_tool is not None:
            self.catchment_map_tool.downstream = self.checkBoxDownstream.isChecked()

    def checkbox_smoothing_state_changed(self, state):
        self.pushbutton_clear_results_clicked()
        # Reset catchment tool is required, because this uses this checkbox info
        if self.catchment_map_tool is not None and self.iface.mapCanvas().mapTool() is self.catchment_map_tool:
            logger.info("Resetting catchment map tool")
            self.iface.mapCanvas().unsetMapTool(self.catchment_map_tool)
            self.catchment_map_tool = CatchmentMapTool(
                    self.iface,
                    parent_button=self.pushButtonClickOnCanvas,
                    gq=self.gq,
                    upstream=self.checkBoxUpstream.isChecked(),
                    downstream=self.checkBoxDownstream.isChecked(),
                    smoothing=self.checkBoxSmoothing.isChecked(),
                )
            self.iface.mapCanvas().setMapTool(self.catchment_map_tool)
            self.pushButtonClickOnCanvas.setChecked(True)

    def checkbox_browse_result_sets_state_changed(self):
        self.spinBoxBrowseResultSets.setEnabled(self.checkBoxBrowseResultSets.isChecked())
        if self.checkBoxBrowseResultSets.isChecked():
            self.gq.filter = [self.spinBoxBrowseResultSets.value()]
        else:
            self.gq.filter = None
        self.gq.zoom_to_results()
        self.iface.mapCanvas().refreshAllLayers()

    def spinbox_browse_result_sets_value_changed(self):
        if self.checkBoxBrowseResultSets.isChecked():
            self.gq.filter = [self.spinBoxBrowseResultSets.value()]
            self.gq.zoom_to_results()
            self.iface.mapCanvas().refreshAllLayers()

    def result_sets_count_changed(self):
        if len(self.gq.result_sets) > 0:
            self.checkBoxBrowseResultSets.setEnabled(True)
            self.spinBoxBrowseResultSets.setMinimum(min(self.gq.result_sets))
            self.spinBoxBrowseResultSets.setMaximum(max(self.gq.result_sets))
            self.spinBoxBrowseResultSets.setValue(max(self.gq.result_sets))
            self.spinbox_browse_result_sets_value_changed()
        else:
            self.checkBoxBrowseResultSets.setEnabled(False)

    def setUpUI(self):
        self.setupUi(self)
        self.mMapLayerComboBoxTargetPolygons.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.QgsFileWidgetSqlite.fileChanged.connect(self.sqlite_selected)
        self.QgsFileWidgetSqlite.setEnabled(False)
        self.doubleSpinBoxThreshold.valueChanged.connect(self.threshold_changed)
        self.doubleSpinBoxThreshold.setSingleStep(1)
        self.doubleSpinBoxThreshold.setMinimum(0)
        self.doubleSpinBoxThreshold.setValue(DEFAULT_THRESHOLD)
        self.doubleSpinBoxStartTime.valueChanged.connect(self.start_time_changed)
        self.doubleSpinBoxEndTime.valueChanged.connect(self.end_time_changed)
        self.checkBoxUpstream.stateChanged.connect(self.checkbox_upstream_state_changed)
        self.checkBoxDownstream.stateChanged.connect(self.checkbox_downstream_state_changed)
        self.pushButtonClickOnCanvas.clicked.connect(self.pushbutton_click_on_canvas_clicked)
        self.pushButtonCatchmentForSelectedNodes.clicked.connect(self.pushbutton_catchment_for_selected_nodes_clicked)
        self.pushButtonCatchmentForPolygons.clicked.connect(self.pushbutton_catchment_for_polygons_clicked)
        self.checkBoxBrowseResultSets.stateChanged.connect(self.checkbox_browse_result_sets_state_changed)
        self.checkBoxSmoothing.stateChanged.connect(self.checkbox_smoothing_state_changed)
        self.spinBoxBrowseResultSets.valueChanged.connect(self.spinbox_browse_result_sets_value_changed)
        self.pushButtonClearResults.clicked.connect(self.pushbutton_clear_results_clicked)

        QgsProject.instance().cleared.connect(self.close)
        self.comboBoxResult.activated.connect(self.select_result)
        self._populate_results()
        self.comboBoxResult.setCurrentIndex(-1)


class UpdateGridAdminTask(QgsTask):
    def __init__(self, description: str, parent: WatershedAnalystDockWidget, gr: GridH5ResultAdmin):
        super().__init__(description, QgsTask.CanCancel)
        self.exception = None
        self.parent = parent
        if not isinstance(gr, GridH5ResultAdmin):
            raise TypeError
        self.gr = gr
        self.parent.setEnabled(False)
        QgsMessageLog.logMessage("Started pre-processing simulation results", MESSAGE_CATEGORY, level=Qgis.Info)

    def run(self):
        try:
            self.parent.gq.gr = self.gr
            return True
        except Exception as e:
            self.exception = e

        return False

    def finished(self, result):
        if self.exception is not None:
            self.parent.setEnabled(True)
            self.parent.widget().repaint()
            raise self.exception

        self.parent.QgsFileWidgetSqlite.setEnabled(result)

        if result:
            self.parent.gq.gr_updated()
            output_timestep_best_guess = int(
                self.parent.gq.gr.nodes.timestamps[-1] / (len(self.parent.gq.gr.nodes.timestamps) - 1)
            )
            start_time = 0
            end_time = int(self.parent.gq.gr.nodes.timestamps[-1])

            self.parent.doubleSpinBoxStartTime.setMaximum(end_time)
            self.parent.doubleSpinBoxStartTime.setSingleStep(output_timestep_best_guess)
            self.parent.doubleSpinBoxStartTime.setValue(start_time)

            self.parent.doubleSpinBoxEndTime.setMaximum(end_time)
            self.parent.doubleSpinBoxEndTime.setSingleStep(output_timestep_best_guess)
            self.parent.doubleSpinBoxEndTime.setValue(end_time)

            if self.parent.gq.result_catchment_layer.receivers(QgsVectorLayer.featureAdded) == 0:
                self.parent.gq.result_catchment_layer.featureAdded.connect(self.parent.result_sets_count_changed)

            if self.parent.gq.result_catchment_layer.receivers(QgsVectorLayer.featuresDeleted) == 0:
                self.parent.gq.result_catchment_layer.featuresDeleted.connect(self.parent.result_sets_count_changed)
            self.parent.setEnabled(True)
            QgsMessageLog.logMessage("Finished pre-processing simulation results", MESSAGE_CATEGORY, level=Qgis.Success)

        else:
            self.parent.setEnabled(True)
            QgsMessageLog.logMessage("Failed pre-processing simulation results", MESSAGE_CATEGORY, level=Qgis.Critical)

    def cancel(self):
        QgsMessageLog.logMessage(
            "Pre-processing simulation results cancelled by user", MESSAGE_CATEGORY, level=Qgis.Info
        )
        super().cancel()
