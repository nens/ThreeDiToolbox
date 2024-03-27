from qgis.analysis import QgsGraphAnalyzer
from qgis.analysis import QgsGraphBuilder
from qgis.analysis import QgsNetworkDistanceStrategy
from qgis.analysis import QgsNetworkStrategy
from qgis.analysis import QgsVectorLayerDirector
from qgis.core import QgsFeature
from qgis.core import QgsFeatureRequest
from qgis.core import QgsField
from qgis.core import QgsMapLayer
from qgis.core import QgsGeometry
from qgis.core import QgsCoordinateTransform
from qgis.gui import QgsMapTool
from qgis.core import QgsPoint
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsVectorLayer
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtCore import QVariant
from qgis.core import QgsProject
from qgis.core import QgsRectangle

import logging
logger = logging.getLogger(__name__)


class AttributeStrategy(QgsNetworkStrategy):
    """Strategy that allows setting a specific attribute for cost"""

    def __init__(self, attribute, attribute_index):
        QgsNetworkStrategy.__init__(self)
        self.attribute = attribute
        self.attribute_index = attribute_index

    def cost(self, distance, feature):
        return feature[self.attribute]

    def requiredAttributes(self):
        # Must be a list of the attribute indexes (int), not strings:
        return [self.attribute_index]


class Route(object):
    def __init__(
        self,
        line_layer,
    ):

        # Make a copy of the line layer containing only 1D lines, and use that to create the graph
        features_1d = [f for f in line_layer.getFeatures() if f["line_type"] in (0, 1, 2, 3, 4, 5)]
        self.graph_layer = QgsVectorLayer(f"linestring?crs={line_layer.crs().authid()}", "graph_lines", "memory")
        self.graph_layer.startEditing()
        self.graph_layer.dataProvider().addAttributes(line_layer.dataProvider().fields().toList())
        self.graph_layer.updateFields()
        self.graph_layer.dataProvider().addFeatures(features_1d)
        self.graph_layer.commitChanges()

        # A search graph is constructed using a so-called Director.
        # Don't use information about road direction from attributes, all edges are treated as two-ways
        self.director = QgsVectorLayerDirector(self.graph_layer, -1, "", "", "", QgsVectorLayerDirector.DirectionBoth)
        self.id_field = "id"
        self.id_field_index = self.graph_layer.fields().lookupField(self.id_field)

        # It is necessary to create a strategy for calculating edge properties.
        self.director.addStrategy(QgsNetworkDistanceStrategy())
        # This second strategy is used to quickly retrieve the id
        self.director.addStrategy(AttributeStrategy(self.id_field, self.id_field_index))
        self.builder = QgsGraphBuilder(line_layer.crs())
        self.director.makeGraph(self.builder, [])
        self.graph = self.builder.graph()

        # init class attributes
        self.start_point_tree = None
        self.id_start_tree = None
        self.has_path = False
        self.tree = []  # Result from Dijkstra
        self.path = []
        self.path_vertexes = []
        self.point_path = []
        self.tree_layer_up_to_date = False
        self._virtual_tree_layer = None
        self.path_points = []

    def get_graph_layer(self) -> QgsVectorLayer:
        return self.graph_layer

    def add_point(self, qgs_point):
        """

        :param qgs_point: QgsPoint instances, additional point
        :return: tuple (boolean: successful added to path,
                        string: message)
        """
        # retrieve vertex index from qgs point
        id_point = self.graph.findVertex(qgs_point)
        if id_point == -1:
            return False, "Please click on a 1D node"
        else:
            distance = 0.0
            if len(self.path_points) > 0:
                # not first point, get path between previous point and point
                success, path, p = self.get_path(
                    self.id_start_tree, id_point, self.path_points[-1][2]
                )

                if not success:
                    # not path found between previous point and point
                    msg = path
                    return False, msg

                self.path.append(path)
                distance = path[-1][1]

                self.path_vertexes.extend(p)
                self.has_path = True

            self.path_points.append((qgs_point, id_point, distance))

            # set (new) tree from last point
            self.set_tree_startpoint(id_point)

            return True, "point found and added to path"

    def get_id_of_point(self, qgs_point):

        return self.graph.findVertex(qgs_point)

    def set_tree_startpoint(self, id_start_point):
        """
        set point (initial or next point) for expending path
        :param qgs_start_point: QgsPoint instance, start point of tree for
                (extension) of path
        :return:
        """
        if id_start_point == -1:
            logger.error("No valid point found")
            return False, "No valid point found"

        # else create tree from this tree startpoint
        self.id_start_tree = id_start_point
        self.start_point_tree = self.graph.vertex(id_start_point).point()

        (self.tree, cost) = QgsGraphAnalyzer.dijkstra(
            self.graph, self.id_start_tree, 0
        )
        self.tree_layer_up_to_date = False
        if self._virtual_tree_layer:
            self.update_virtual_tree_layer()

    @staticmethod
    def aggregate_route_parts(route_part):
        """This function yields route segments, but combines segments belonging to the same feature"""
        for count, (begin_dist, end_dist, _, direction, feature) in enumerate(route_part):
            if count == 0:
                last_feature = feature
                feature_begin_dist = begin_dist
                feature_end_dist = end_dist
                feature_direction = direction
                continue
            if feature["id"] == last_feature["id"]:
                feature_end_dist = end_dist
                continue
            yield feature_begin_dist, feature_end_dist, feature_direction, last_feature
            last_feature = feature
            feature_begin_dist = begin_dist
            feature_end_dist = end_dist
            feature_direction = direction
        yield feature_begin_dist, feature_end_dist, feature_direction, last_feature

    def get_path(self, id_start_point, id_end_point, begin_distance=0):
        """
        get path between the two graph points
        :param id_start_point: graph identifier of start point of (sub)path
        :param id_end_point: graph identifier of end point of (sub) path
        :param begin_distance: start distance of cumulative path distance
        :return: tuple with 3 values:
                 - successful found a path
                 - Message in case of not succesful found a path or
                   a list of path line elements, represent as a tuple, with:
                   - begin distance of part (from initial start_point),
                   - end distance of part (from initial start_point)
                   - Length of line segment
                   - direction of path equal to direction of feature definition
                     1 in case ot is, -1 in case it is the opposite direction
                   - feature
                 - list of vertexes (graph nodes)
        """

        # check if end_point is connected to start point
        if self.tree[id_end_point] == -1:
            logger.error("Path not found")
            return False, "Path not found", None

        # else continue finding path
        p = []
        path_props = []
        cum_dist = begin_distance
        cur_pos = id_end_point
        while cur_pos != id_start_point:
            point = self.graph.vertex(
                self.graph.edge(self.tree[cur_pos]).toVertex()
            ).point()
            p.append(point)

            dist = self.graph.edge(self.tree[cur_pos]).cost(0)
            id_line = self.graph.edge(self.tree[cur_pos]).cost(1)

            filt = u'"%s" = %s' % (self.id_field, str(id_line))
            request = QgsFeatureRequest().setFilterExpression(filt)
            feature = next(self.graph_layer.getFeatures(request))

            # In order to determine the direction of this segment in the path,
            # compare the first point on the feature to the first vertex of
            # the geometry. In case the previous segment belonged to the
            # same feature, take that direction.
            if len(path_props) > 0 and path_props[0][4]["id"] == feature["id"]:
                route_direction_feature = path_props[0][3]
            else:
                if QgsPoint(point.x(), point.y()) == feature.geometry().vertexAt(0):
                    route_direction_feature = -1
                else:
                    route_direction_feature = 1

            path_props.insert(0, [None, None, dist, route_direction_feature, feature])

            cur_pos = self.graph.edge(self.tree[cur_pos]).fromVertex()

        for path in path_props:
            path[0] = cum_dist
            cum_dist += path[2]
            path[1] = cum_dist

        p.append(self.start_point_tree)

        return True, path_props, reversed(p)

    def update_virtual_tree_layer(self):
        """
        update virtual layer with latest tree
        :return: boolean, successful updated
        """

        if not self._virtual_tree_layer:
            # not yet created
            return

        if self.tree_layer_up_to_date:
            return

        ids = [feat.id() for feat in self._virtual_tree_layer.getFeatures()]
        self._virtual_tree_layer.dataProvider().deleteFeatures(ids)

        features = []
        for branch in self.tree:
            # make int, compare with long doesn't work (?!)
            if int(branch) >= 0:
                # add a feature
                feat = QgsFeature()
                a = self.graph.vertex(self.graph.edge(branch).fromVertex()).point()
                b = self.graph.vertex(self.graph.edge(branch).toVertex()).point()
                feat.setGeometry(QgsGeometry.fromPolylineXY([a, b]))

                feat.setAttributes(
                    [
                        float(self.graph.edge(branch).cost(0)),
                        int(self.graph.edge(branch).cost(1)),
                    ]
                )
                features.append(feat)

        self._virtual_tree_layer.dataProvider().addFeatures(features)
        self._virtual_tree_layer.commitChanges()
        self._virtual_tree_layer.updateExtents()
        self._virtual_tree_layer.triggerRepaint()
        self._virtual_tree_layer.setFlags(QgsMapLayer.Private)

    def get_virtual_tree_layer(self):
        """
        return a (link to) an in memory QgsVectorLayer of the current active
        tree. The layer will be updated during when the tree (or tree start
        point) changes
        :return: QgsVectorLayer in memory.
        """
        if not self._virtual_tree_layer:

            self._virtual_tree_layer = QgsVectorLayer(
                f"linestring?crs={self.graph_layer.crs().authid()}", "temporary_lines", "memory"
            )

            self._virtual_tree_layer.dataProvider().addAttributes(
                [
                    QgsField("weight", QVariant.Double),
                    QgsField("line_id", QVariant.LongLong),
                ]
            )

        if not self.tree_layer_up_to_date:
            self.update_virtual_tree_layer()

        return self._virtual_tree_layer

    def reset(self):
        """
        reset found route
        """

        self.id_start_tree = None
        self.start_point_tree = None
        self.cost = []
        self.tree = []
        self.has_path = False
        self.path_points = []
        self.path = []
        self.path_vertexes = []
        self.update_virtual_tree_layer()


class RouteMapTool(QgsMapTool):
    def __init__(self, canvas, graph_layer, callback_on_select):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.graph_layer = graph_layer
        self.callback_on_select = callback_on_select

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        # use 5 pixels for selecting
        point_ll = self.canvas.getCoordinateTransform().toMapCoordinates(x - 5, y - 5)
        point_ru = self.canvas.getCoordinateTransform().toMapCoordinates(x + 5, y + 5)
        rect = QgsRectangle(
            min(point_ll.x(), point_ru.x()),
            min(point_ll.y(), point_ru.y()),
            max(point_ll.x(), point_ru.x()),
            max(point_ll.y(), point_ru.y()),
        )

        transform = QgsCoordinateTransform(
            self.canvas.mapSettings().destinationCrs(),
            self.graph_layer.crs(),
            QgsProject.instance(),
        )

        rect = transform.transform(rect)
        filter = QgsFeatureRequest().setFilterRect(rect)
        selected = self.graph_layer.getFeatures(filter)

        clicked_point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        transformed_point = transform.transform(clicked_point)

        selected_points = [s for s in selected]
        if len(selected_points) > 0:
            self.callback_on_select(selected_points, transformed_point)

    def activate(self):
        self.canvas.setCursor(QCursor(Qt.CrossCursor))

    def deactivate(self):
        self.deactivated.emit()
        self.canvas.setCursor(QCursor(Qt.ArrowCursor))

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return False
