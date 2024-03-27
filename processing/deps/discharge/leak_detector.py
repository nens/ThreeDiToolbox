from datetime import datetime
from typing import Dict, Union, List, Tuple, Optional, Iterator

import numpy as np
from osgeo import gdal
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from scipy.ndimage import label, generate_binary_structure
from scipy.signal import find_peaks
from threedigrid.admin.gridadmin import GridH5Admin
from threedigrid.admin.lines.models import Lines

SEARCH_STRUCTURE = generate_binary_structure(2, 2)
TOP = 'top'
RIGHT = 'right'
BOTTOM = 'bottom'
LEFT = 'left'
LEFTHANDSIDE = "left-hand side"
RIGHTHANDSIDE = "right-hand side"
NA = 'N/A'
SIDE_INDEX = {
    TOP: np.index_exp[0, :],
    RIGHT: np.index_exp[:, -1],
    BOTTOM: np.index_exp[-1, :],
    LEFT: np.index_exp[:, 0]
}
OPPOSITE = {
    LEFT: RIGHT,
    RIGHT: LEFT,
    TOP: BOTTOM,
    BOTTOM: TOP
}
REFERENCE = 'reference'
NEIGH = 'neigh'
MERGED = 'merged'
COORD_DECIMALS = 5
PSEUDO_INFINITE = 9999

gdal.UseExceptions()


def read_as_array(
        raster: gdal.Dataset,
        bbox: Union[List[float], Tuple[float], np.ndarray],
        band_nr: int = 1,
        pad: bool = False,
        decimals: int = 5
) -> np.ndarray:
    """
    Read part of raster that intersects with bounding box in geo coordinates as array

    :param band_nr: band number
    :param raster: input raster dataset
    :param bbox: Bounding box corner coordinates in the input rasters crs: [x0, y0, x1, y1]
    :param pad: pad with nodata value if partially out of extent. alternatively, return only the part of input raster
    that intersects with the bbox
    :param decimals: `coords` are rounded to `decimals`

    """
    band = raster.GetRasterBand(band_nr)
    gt = raster.GetGeoTransform()
    inv_gt = gdal.InvGeoTransform(gt)
    x0, y0 = (round(val, decimals) for val in gdal.ApplyGeoTransform(inv_gt, float(bbox[0]), float(bbox[1])))
    x1, y1 = (round(val, decimals) for val in gdal.ApplyGeoTransform(inv_gt, float(bbox[2]), float(bbox[3])))
    xmin, ymin = min(x0, x1), min(y0, y1)
    xmax, ymax = max(x0, x1), max(y0, y1)
    if xmin > raster.RasterXSize or ymin > raster.RasterYSize or xmax < 0 or ymax < 0:
        raise ValueError('bbox does not intersect with raster')

    intersection_xmin, intersection_ymin = max(xmin, 0), max(ymin, 0)
    intersection_xmax, intersection_ymax = min(xmax, raster.RasterXSize), min(ymax, raster.RasterYSize)
    arr = band.ReadAsArray(
        int(intersection_xmin),
        int(intersection_ymin),
        int(intersection_xmax - intersection_xmin),
        int(intersection_ymax - intersection_ymin)
    )
    if pad:
        ndv = band.GetNoDataValue()
        arr_pad = np.pad(
            arr,
            ((int(intersection_ymin - ymin), int(ymax - intersection_ymax)),
             (int(intersection_xmin - xmin), int(xmax - intersection_xmax))),
            'constant',
            constant_values=((ndv, ndv), (ndv, ndv))
        )
        return arr_pad
    else:
        return arr


def filter_lines_by_node_ids(lines: Lines, node_ids: np.array):
    boolean_mask = np.sum(np.isin(lines.line_nodes, node_ids), axis=1) > 0
    line_ids = lines.id[boolean_mask]
    result = lines.filter(id__in=line_ids)
    return result


def intersection(
        line_coords1,
        line_coords2,
        decimals: int = 5
) -> Optional[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """Returns None if no intersection is found"""
    (start_x1, start_y1), (end_x1, end_y1) = np.round(line_coords1, decimals)
    (start_x2, start_y2), (end_x2, end_y2) = np.round(line_coords2, decimals)
    if start_x1 == end_x1 == start_x2 == end_x2 == start_x1:
        x = start_x1
        if (start_y1 >= start_y2 and end_y1 <= end_y2) or (start_y2 >= start_y1 and end_y2 <= end_y1):
            return (x, max(start_y1, start_y2)), (x, min(end_y1, end_y2))
    elif start_y1 == end_y1 == start_y2 == end_y2:
        y = start_y1
        if (start_x1 >= start_x2 and end_x1 <= end_x2) or (start_x2 >= start_x1 and end_x2 <= end_x1):
            return (max(start_x1, start_x2), y), (min(end_x1, end_x2), y)
    return None


class LeakDetector:
    """
    Interface between the gridadmin and the classes in this module
    Maintains an administration of cells, edges and obstacles
    """

    def __init__(
            self,
            gridadmin: GridH5Admin,
            dem: gdal.Dataset,
            flowline_ids: List[int],
            min_obstacle_height: float,
            search_precision: float = None,
            min_peak_prominence: float = None,
            obstacles: List[Tuple[LineString, float]] = None,
            feedback=None
    ):
        """
        :param gridadmin:
        :param dem:
        :param flowline_ids: list of flowline ids to limit the obstacle detection to. Only 2D_OPEN_WATER flowlines used.
        :param min_obstacle_height:
        :param search_precision:
        :param min_peak_prominence:
        :param feedback: Object that has .pushWarning() method, like QgsProcessingFeedback
        """
        self.dem = dem
        self.min_obstacle_height = min_obstacle_height
        self.search_precision = search_precision or self.suitable_search_precision()
        self.min_peak_prominence = min_peak_prominence or min_obstacle_height

        self.flowlines = gridadmin.lines.subset('2D_OPEN_WATER').filter(id__in=flowline_ids)
        self.flowlines__id = self.flowlines.id
        if np.all(np.isnan(self.flowlines.dpumax)):
            if not obstacles:
                if feedback:
                    feedback.pushWarning(
                        "Gridadmin file does not contain elevation data. Exchange levels will be derived from the DEM. "
                        "Obstacles were not supplied and will be ignored."
                    )
        self.flowlines__line_nodes = self.bind_to_flowline_ids(self.flowlines.line_nodes)
        self.flowlines__line_coords = self.bind_to_flowline_ids(self.flowlines.line_coords.T)

        # Create cells
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Read cells...")
        unique_cell_ids = np.unique(np.squeeze(self.flowlines.line_nodes.data))
        cells__cell_coords = dict(zip(gridadmin.cells.filter(id__in=unique_cell_ids).id, np.round(gridadmin.cells.filter(id__in=unique_cell_ids).cell_coords.T, COORD_DECIMALS)))

        self._cell_dict = dict()
        for i, (cell_id, cell_coords) in enumerate(cells__cell_coords.items()):
            if feedback:
                if feedback.isCanceled():
                    return
            self._cell_dict[cell_id] = Cell(ld=self, id=cell_id, coords=cell_coords)
            if feedback:
                feedback.setProgress(100 * i / len(cells__cell_coords))

        # Find cell neighbours
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Find cell neighbours...")
        for i, flowline_id in enumerate(self.flowlines__id):
            if feedback:
                if feedback.isCanceled():
                    return
            cell_ids: Tuple = self.flowlines__line_nodes[flowline_id]
            reference_cell = self.cell(cell_ids[0])
            neigh_cell = self.cell(cell_ids[1])
            location = reference_cell.locate_cell(neigh_cell, neigh_is_next=True)
            reference_cell.add_neigh(neigh_cell=neigh_cell, location=location)
            neigh_cell.add_neigh(neigh_cell=reference_cell, location=OPPOSITE[location])
            if feedback:
                feedback.setProgress(100 * i / len(self.flowlines__id))

        # Create edges
        if feedback:
            feedback.pushInfo(f"{datetime.now()}")
            feedback.setProgressText("Create edges...")
        self.edges = list()
        self._edge_by_line_nodes = dict()  # {line_nodes: Edge}
        self._edge_by_flowline_id = dict()  # {flowline_id: Edge}
        for i, flowline_id in enumerate(self.flowlines__id):
            if feedback:
                if feedback.isCanceled():
                    return
            cell_ids = tuple(self.flowlines__line_nodes[flowline_id])
            edge = Edge(
                ld=self,
                cell_ids=cell_ids,
                flowline_id=flowline_id,
            )
            edge.calculate_geometries(flowline_coords=self.flowlines__line_coords[flowline_id])
            edge.calculate_exchange_levels(
                # exchange_level=flowline["dpumax"]  # Commented out because of a bug in how Tables writes to h5 file
            )
            self.edges.append(edge)
            self._edge_by_line_nodes[cell_ids] = edge
            self._edge_by_flowline_id[flowline_id] = edge
            if feedback:
                feedback.setProgress(100 * i / len(self.flowlines__id))

        # Update edge exchange level from obstacles
        if obstacles:
            if feedback:
                feedback.pushInfo(f"{datetime.now()}")
                feedback.setProgressText("Update edge exchange level from obstacles...")
                feedback.setProgress(0)
            flowline_geometries = [edge.flowline_geometry for edge in self.edges]
            flowline_geometry_tree = STRtree(flowline_geometries)
            if feedback:
                if feedback.isCanceled():
                    return
            obstacle_flowline_intersection = flowline_geometry_tree.query(
                [obstacle[0] for obstacle in obstacles],
                predicate='intersects'
            )
            if feedback:
                if feedback.isCanceled():
                    return
            obstacle_indices = np.unique(obstacle_flowline_intersection[0, :])
            edge_indices = np.split(
                obstacle_flowline_intersection[1, :],
                np.unique(obstacle_flowline_intersection[0, :], return_index=True)[1][1:]
            )  # "group by", see https://stackoverflow.com/a/43094244/5780984
            edge_finder = dict(zip(obstacle_indices, edge_indices))
            for obstacle_index in obstacle_indices:
                if feedback:
                    if feedback.isCanceled():
                        return
                crest_level = obstacles[obstacle_index][1]
                intersected_edge_indices = edge_finder[obstacle_index]
                for i in intersected_edge_indices:
                    edge = self.edges[i]
                    if edge.exchange_level < crest_level:
                        edge.exchange_level = crest_level
                feedback.setProgress(100 * i / len(obstacle_indices))

    def suitable_search_precision(self):
        return min(self.min_obstacle_height/10, 0.1)

    def bind_to_flowline_ids(self, obj):
        """
        Return a dict of {flowline_id: obj_item} pairs
        :param obj:
        :return:
        """
        return dict(zip(self.flowlines__id, obj))

    @property
    def cells(self) -> List:
        return list(self._cell_dict.values())

    def cell(self, cell_id):
        """
        Return the cell indicated by `cell_id`
        """
        return self._cell_dict[cell_id]

    def edge(self, reference_cell, neigh_cell):
        """
        Find the edge between reference_cell (left/bottom) and neigh_cell (top/right)

        :param reference_cell: cell or cell id
        :param neigh_cell: cell or cell id of a cell to the top or right of reference cell
        """
        if isinstance(reference_cell, Cell):
            reference_cell = reference_cell.id
        if isinstance(neigh_cell, Cell):
            neigh_cell = neigh_cell.id
        return self._edge_by_line_nodes[(reference_cell, neigh_cell)]

    def get_edge_by_flowline_id(self, flowline_id):
        return self._edge_by_flowline_id[flowline_id]

    def cell_pairs(self):
        """Return an interator of all cell pairs that can be created by using the cell_ids as reference cell"""
        for reference_cell in self.cells:
            neigh_cells = reference_cell.neigh_cells[TOP] + reference_cell.neigh_cells[RIGHT]
            for neigh_cell in neigh_cells:
                cell_pair = CellPair(self, reference_cell, neigh_cell)
                yield cell_pair

    def run(self, feedback=None):
        """
        Find all obstacles

        :param feedback: Object that has `setProgress()`, `isCanceled()` and `pushInfo()` methods,
        like QgsProcessingFeedback
        :return: None
        """

        # find obstacles
        for i, cell_pair in enumerate(self.cell_pairs()):
            try:
                cell_pair.find_obstacles()
                if feedback:
                    feedback.setProgress(50 * ((i + 1) / len(self.flowlines__id)))
                    if feedback.isCanceled():
                        return
            except Exception as e:
                print(f"Something went wrong in cell pair ({cell_pair.reference_cell.id, cell_pair.neigh_cell.id})")
                raise e

        # find connecting obstacles
        for i, cell_pair in enumerate(self.cell_pairs()):
            try:
                cell_pair.find_connecting_obstacles()
                if feedback:
                    feedback.setProgress(50 + 50 * ((i + 1) / len(self.flowlines__id)))
                    if feedback.isCanceled():
                        return
            except IndexError as e:
                print(f"Something went wrong in cell pair ({cell_pair.reference_cell.id, cell_pair.neigh_cell.id})")
                raise e

    def results(self, geometry: str, flowline_ids=None) -> Iterator[Dict]:
        """
        Iterate over all edges that have an obstacle
        Return results for all edges if flowline_ids is not specified, or results for specific flowlines only
        `geometry` can be 'EDGE' or 'OBSTACLE'
        """
        for edge in self.edges:
            if flowline_ids is None or edge.flowline_id in flowline_ids:
                if edge.obstacles:
                    yield edge.as_dict(geometry=geometry)


class Obstacle:
    """
    Obstacle between two sides of a CellPair
    """

    def __init__(
            self,
            ld: LeakDetector,
            crest_level,
            from_cell,
            to_cell,
            from_pos: Tuple[int, int],
            to_pos: Tuple[int, int],
            from_side: str = None,
            to_side: str = None,
            edges=None
    ):
        self.ld = ld
        self.crest_level = crest_level
        self.from_cell = from_cell
        self.to_cell = to_cell
        self.from_side = from_side
        self.to_side = to_side
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.edges = edges if edges else []
        self._from_edge = None
        self._to_edge = None

        # calculate geometry
        gt = self.ld.dem.GetGeoTransform()
        from_pos_y = self.from_pos[0]
        from_pos_x = self.from_pos[1]
        to_pos_y = self.to_pos[0]
        to_pos_x = self.to_pos[1]
        from_x = self.from_cell.coords[0] + from_pos_x * abs(gt[1]) + abs(gt[1]) / 2
        from_y = self.from_cell.coords[3] - (from_pos_y * abs(gt[5]) + abs(gt[5]) / 2)
        to_x = self.to_cell.coords[0] + to_pos_x * abs(gt[1]) + abs(gt[1]) / 2
        to_y = self.to_cell.coords[3] - (to_pos_y * abs(gt[5]) + abs(gt[5]) / 2)
        self.geometry = LineString([Point(from_x, from_y), Point(to_x, to_y)])

    @staticmethod
    def _find_edge(cell, side, pos):
        if side is None:
            raise ValueError("Cannot identify edge if from_edge or to_edge has not been set")
        edges = cell.edges(side)
        if len(edges) == 0:
            return None  # e.g. cell at model boundary
        if side in [TOP, BOTTOM]:
            # edge ordering is determined by x ordinate (col index)
            if pos[1] + 1 > cell.width / 2:
                return edges[-1]
            else:
                return edges[0]
        elif side in [LEFT, RIGHT]:
            # edge ordering is determined by y ordinate (row index)
            if pos[0] + 1 > cell.height / 2:
                return edges[-1]
            else:
                return edges[0]
        else:
            raise ValueError(f"Invalid value for parameter side: {side}")

    @property
    def from_edge(self):
        if not self._from_edge:
            self._from_edge = self._find_edge(cell=self.from_cell, side=self.from_side, pos=self.from_pos)
        return self._from_edge

    @from_edge.setter
    def from_edge(self, edge):
        self._from_edge = edge

    @property
    def to_edge(self):
        if not self._to_edge:
            self._to_edge = self._find_edge(cell=self.to_cell, side=self.to_side, pos=self.to_pos)
        return self._to_edge

    @to_edge.setter
    def to_edge(self, edge):
        self._to_edge = edge


class Edge:
    """
    Edge between two cells
    Drawing direction is always left -> right or bottom -> top.
    """

    def __init__(
            self,
            ld: LeakDetector,
            cell_ids: Tuple[int],
            flowline_id: int
    ):
        self.ld = ld
        self.cell_ids = cell_ids
        self.flowline_id = flowline_id
        self.obstacles: List[Obstacle] = list()

        # attributes set in calculate_geometries()
        self.flowline_geometry = None
        self.geometry = None
        self.start_coord = None
        self.end_coord = None

        # attributes set in calculate_exchange_level()
        self.exchange_level = None
        self.exchange_levels = None

    def calculate_geometries(self, flowline_coords: Tuple[float, float, float, float]):
        """
        Set the geometries of the edge and the flowline crossing the edge
        sets `self.flowline_geometry`, `self.geometry`, `self.start_coord`, `self.end_coord`
        """
        x0, y0, x1, y1 = flowline_coords
        self.flowline_geometry = LineString([Point(x0, y0), Point(x1, y1)])

        # set start and end coordinates
        cell_1, cell_2 = [self.ld.cell(i) for i in self.cell_ids]
        side_coords1 = cell_1.side_coords()
        side_coords2 = cell_2.side_coords()
        for side_1 in [TOP, BOTTOM, LEFT, RIGHT]:
            for side_2 in [TOP, BOTTOM, LEFT, RIGHT]:
                intersection_coords = intersection(side_coords1[side_1], side_coords2[side_2])
                if intersection_coords:
                    self.start_coord, self.end_coord = intersection_coords
        self.geometry = LineString([Point(*self.start_coord), Point(*self.end_coord)])

    def calculate_exchange_levels(self, exchange_level: float = None):
        """
        Sets `self.exchange_level`, `self.exchange_levels`
        If `exchange_level` is None, exchange_level(s) will be read from the DEM
        """
        # set exchange_level
        if exchange_level is not None:
            if np.isnan(exchange_level):
                exchange_level = None
            self.exchange_level = exchange_level
        else:
            # calculate exchange level from DEM: 1D array of max of pixel pairs along the edge
            pxsize = self.ld.dem.GetGeoTransform()[1]
            if self.is_bottom_up:
                bbox = [self.start_coord[0] - pxsize, self.start_coord[1], self.end_coord[0] + pxsize,
                        self.end_coord[1]]
            else:
                bbox = [self.start_coord[0], self.start_coord[1] - pxsize, self.end_coord[0],
                        self.end_coord[1] + pxsize]
            arr = read_as_array(raster=self.ld.dem, bbox=bbox, pad=True)
            self.exchange_levels = np.nanmax(arr, axis=int(self.is_bottom_up))
            self.exchange_level = np.nanmin(self.exchange_levels)

    @property
    def is_bottom_up(self):
        return self.start_coord[0] == self.end_coord[0]

    def as_dict(self, geometry: str):
        if geometry == 'EDGE':
            geom = self.geometry
        elif geometry == 'OBSTACLE':
            geom = highest(self.obstacles).geometry if self.obstacles else None
        else:
            raise ValueError(f"'geometry' must be 'EDGE' or 'OBSTACLE', not {geometry}")
        return {
            "flowline_id": self.flowline_id,
            "exchange_level": self.exchange_level,
            "crest_level": highest(self.obstacles).crest_level if self.obstacles else None,
            "geometry": geom
        }


class Cell:
    """
    Cell in a computational grid, including an array of DEM pixel values
    """

    def __init__(
            self,
            ld: LeakDetector,
            id: int,
            coords: np.ndarray
    ):
        """
        :param id: cell id
        :param ld:
        :param coords: corner coordinates the crs of the dem: [min_x, min_y, max_x, max_y]
        """
        self.ld = ld
        self.id = id
        self.coords = coords
        self.xmax = np.max(coords[[0, 2]])
        self.xmin = np.min(coords[[0, 2]])
        self.pixels = read_as_array(raster=ld.dem, bbox=coords, pad=True)
        band = ld.dem.GetRasterBand(1)
        ndv = band.GetNoDataValue()
        maxval = np.nanmax(self.pixels)
        self.pixels[self.pixels == ndv] = maxval + ld.min_obstacle_height + ld.search_precision
        self.width = self.pixels.shape[1]
        self.height = self.pixels.shape[0]
        self.neigh_cells = {TOP: [], RIGHT: [], BOTTOM: [], LEFT: []}

    def locate_cell(self, neigh_cell, neigh_is_next: bool) -> str:
        if neigh_is_next:
            if self.xmax == neigh_cell.xmin:  # aligned horizontally if True
                return RIGHT
            else:
                return TOP
        else:
            if self.xmin == neigh_cell.xmax:  # aligned horizontally if True
                return LEFT
            else:
                return BOTTOM

    def add_neigh(self, neigh_cell, location: str):
        self.neigh_cells[location].append(neigh_cell)

    def edges(self, primary_location: str, secondary_location: Union[str, int] = None) -> Union[Edge, List[Edge]]:
        """Returns list of Edges, or, if secondary location is specified, a single Edge"""
        if isinstance(secondary_location, str):
            loc_idx_mapping = {
                LEFT: 0,
                RIGHT: -1,
                BOTTOM: 0,
                TOP: -1
            }
            secondary_location = loc_idx_mapping[secondary_location]
        edges_dict = {
            TOP: [self.ld.edge(self, i) for i in self.neigh_cells[TOP]],
            BOTTOM: [self.ld.edge(i, self) for i in self.neigh_cells[BOTTOM]],
            LEFT: [self.ld.edge(i, self) for i in self.neigh_cells[LEFT]],
            RIGHT: [self.ld.edge(self, i) for i in self.neigh_cells[RIGHT]]
        }
        edges = sorted(edges_dict[primary_location], key=lambda a: a.start_coord)
        if not edges:
            return list()
        elif secondary_location is not None:
            return edges[secondary_location]
        else:
            return edges

    def side_coords(self):
        """Return dict with the coordinates of all sides of the cell"""
        xmin, ymin, xmax, ymax = self.coords
        return {
            TOP: ((xmin, ymax), (xmax, ymax)),
            BOTTOM: ((xmin, ymin), (xmax, ymin)),
            LEFT: ((xmin, ymin), (xmin, ymax)),
            RIGHT: ((xmax, ymin), (xmax, ymax)),
        }

    def side_indices(self, side: str) -> np.array:
        """
        Return an array of two rows
         - row 0: row indices
         - row 1: col indices
        """
        indices = np.indices(self.pixels.shape)
        x = indices[0][SIDE_INDEX[side]]
        y = indices[1][SIDE_INDEX[side]]
        return np.vstack([x, y])

    def edge_pixels(self, side: str) -> np.array:
        """
        Return the pixels on the inside of given `edge`
        Pixel values are sorted from TOP to BOTTOM or from LEFT to RIGHT
        """
        return self.pixels[SIDE_INDEX[side]]

    def maxima(self, side):
        """
        Return the pixel indices of the local maxima (peaks) along the edge at given `side`
        """

        maxima_1d, _ = find_peaks(self.edge_pixels(side), prominence=self.ld.min_peak_prominence)
        if side == TOP:
            row_indices = np.zeros(maxima_1d.shape)
            result = np.vstack([row_indices, maxima_1d]).T.astype(int)

        elif side == BOTTOM:
            row_indices = np.ones(maxima_1d.shape) * (self.height - 1)
            result = np.vstack([row_indices, maxima_1d]).T.astype(int)

        elif side == LEFT:
            col_indices = np.zeros(maxima_1d.shape)
            result = np.vstack([maxima_1d, col_indices]).T.astype(int)

        elif side == RIGHT:
            col_indices = np.ones(maxima_1d.shape) * (self.width - 1)
            result = np.vstack([maxima_1d, col_indices]).T.astype(int)

        return result

    def locate_edge(self, edge):
        for side in [TOP, BOTTOM, LEFT, RIGHT]:
            for cell_edge in self.edges(side):
                if edge == cell_edge:
                    return side
        return None


class CellPair:
    """
    A pair of neighbouring cells
    The reference cell is always the left / bottom of the pair
    """

    def __init__(self, ld: LeakDetector, reference_cell: Cell, neigh_cell: Cell):
        self.ld = ld
        self.reference_cell = reference_cell
        self.neigh_cell = neigh_cell
        self.cells = {REFERENCE: self.reference_cell, NEIGH: self.neigh_cell}
        self.neigh_primary_location, self.neigh_secondary_location = self.locate_cell(NEIGH)
        if self.neigh_primary_location not in [TOP, RIGHT]:
            raise ValueError(
                f"neigh_cell is located at the {self.neigh_primary_location} of reference_cell. It must be located at "
                f"the top or right of reference_cell"
            )
        self.reference_primary_location, self.reference_secondary_location = self.locate_cell(REFERENCE)
        smallest_cell = self.smallest()
        if smallest_cell:
            fill_array = smallest_cell.pixels * 0 - min(np.nanmin(reference_cell.pixels), np.nanmin(neigh_cell.pixels))
            if reference_cell.id == smallest_cell.id:
                smallest_secondary_location = self.reference_secondary_location
            else:
                smallest_secondary_location = self.neigh_secondary_location

        if self.neigh_primary_location == TOP:
            if not smallest_cell:
                self.pixels = np.vstack([neigh_cell.pixels, reference_cell.pixels])
            else:
                if smallest_secondary_location == LEFT:
                    smallest_cell_pixels = np.hstack([smallest_cell.pixels, fill_array])
                else:
                    smallest_cell_pixels = np.hstack([fill_array, smallest_cell.pixels])
                if reference_cell.id == smallest_cell.id:
                    self.pixels = np.vstack([neigh_cell.pixels, smallest_cell_pixels])
                else:
                    self.pixels = np.vstack([smallest_cell_pixels, reference_cell.pixels])

        elif self.neigh_primary_location == RIGHT:
            if not smallest_cell:
                self.pixels = np.hstack([reference_cell.pixels, neigh_cell.pixels])
            else:
                if smallest_secondary_location == TOP:
                    smallest_cell_pixels = np.vstack([smallest_cell.pixels, fill_array])
                else:
                    smallest_cell_pixels = np.vstack([fill_array, smallest_cell.pixels])
                if reference_cell.id == smallest_cell.id:
                    self.pixels = np.hstack([smallest_cell_pixels, neigh_cell.pixels])
                else:
                    self.pixels = np.hstack([reference_cell.pixels, smallest_cell_pixels])

        elif self.neigh_primary_location == BOTTOM:
            if not smallest_cell:
                self.pixels = np.vstack([reference_cell.pixels, neigh_cell.pixels])
            else:
                if smallest_secondary_location == LEFT:
                    smallest_cell_pixels = np.hstack([smallest_cell.pixels, fill_array])
                else:
                    smallest_cell_pixels = np.hstack([fill_array, smallest_cell.pixels])
                if reference_cell.id == smallest_cell.id:
                    self.pixels = np.vstack([smallest_cell_pixels, neigh_cell.pixels])
                else:
                    self.pixels = np.vstack([reference_cell.pixels, smallest_cell_pixels])

        elif self.neigh_primary_location == LEFT:
            if not smallest_cell:
                self.pixels = np.hstack([neigh_cell.pixels, reference_cell.pixels])
            else:
                if smallest_secondary_location == TOP:
                    smallest_cell_pixels = np.vstack([smallest_cell.pixels, fill_array])
                else:
                    smallest_cell_pixels = np.vstack([fill_array, smallest_cell.pixels])
                if reference_cell.id == smallest_cell.id:
                    self.pixels = np.hstack([neigh_cell.pixels, smallest_cell_pixels])
                else:
                    self.pixels = np.hstack([smallest_cell_pixels, reference_cell.pixels])
        else:
            raise ValueError("Input cells are not neighbours")
        self.width = self.pixels.shape[1]
        self.height = self.pixels.shape[0]

        # Determine shifts, i.e. paramaters to transform coordinates between ref cell, neigh cell and merged
        # {pos in ref cell} + self.reference_cell_shift = {pos in merged pixels}
        # {pos in neigh cell} + self.neigh_cell_shift = {pos in merged pixels}

        # Reference
        # x
        if self.neigh_primary_location == LEFT:
            reference_cell_shift_x = self.neigh_cell.width
        elif self.reference_secondary_location == RIGHT:
            reference_cell_shift_x = self.reference_cell.width
        else:
            reference_cell_shift_x = 0

        # y
        if self.neigh_primary_location == TOP:
            reference_cell_shift_y = self.neigh_cell.height
        elif self.reference_secondary_location == BOTTOM:
            reference_cell_shift_y = self.reference_cell.height
        else:
            reference_cell_shift_y = 0

        # Neigh
        # x
        if self.neigh_primary_location == RIGHT:
            neigh_cell_shift_x = self.reference_cell.width
        elif self.neigh_secondary_location == RIGHT:
            neigh_cell_shift_x = self.neigh_cell.width
        else:
            neigh_cell_shift_x = 0

        # y
        if self.neigh_primary_location == BOTTOM:
            neigh_cell_shift_y = self.reference_cell.height
        elif self.neigh_secondary_location == BOTTOM:
            neigh_cell_shift_y = self.neigh_cell.height
        else:
            neigh_cell_shift_y = 0

        self.reference_cell_shift = (reference_cell_shift_y, reference_cell_shift_x)
        self.neigh_cell_shift = (neigh_cell_shift_y, neigh_cell_shift_x)

        # Set edges
        self.edges = {}
        if self.neigh_primary_location == TOP:
            self.edges[0] = self.reference_cell.edges(BOTTOM)
            self.edges[1] = [self.ld.edge(self.reference_cell, self.neigh_cell)]
            self.edges[2] = self.neigh_cell.edges(TOP)
        if self.neigh_primary_location == RIGHT:
            self.edges[0] = self.reference_cell.edges(LEFT)
            self.edges[1] = [self.ld.edge(self.reference_cell, self.neigh_cell)]
            self.edges[2] = self.neigh_cell.edges(RIGHT)

    @property
    def bottom_aligned(self) -> bool:
        return round(self.reference_cell.coords[1], COORD_DECIMALS) == round(self.neigh_cell.coords[1], COORD_DECIMALS)

    @property
    def top_aligned(self) -> bool:
        return round(self.reference_cell.coords[3], COORD_DECIMALS) == round(self.neigh_cell.coords[3], COORD_DECIMALS)

    @property
    def left_aligned(self) -> bool:
        return round(self.reference_cell.coords[0], COORD_DECIMALS) == round(self.neigh_cell.coords[0], COORD_DECIMALS)

    @property
    def right_aligned(self) -> bool:
        return round(self.reference_cell.coords[2], COORD_DECIMALS) == round(self.neigh_cell.coords[2], COORD_DECIMALS)

    @property
    def lowest_edge(self):
        return lowest(self.edges[0] + self.edges[1] + self.edges[2])

    def locate_pos(self, pos: Tuple[int, int]) -> str:
        """
        Returns the cell ('reference' or 'neigh') in which given pixel position (index) is located
        """
        self.pixels[pos]  # to raise IndexError if out of bounds for this CellPair
        if self.neigh_primary_location == TOP:
            if pos[0] >= self.neigh_cell.height:
                return REFERENCE
            else:
                return NEIGH
        if self.neigh_primary_location == RIGHT:
            if pos[1] >= self.reference_cell.width:
                return NEIGH
            else:
                return REFERENCE

    def locate_cell(self, which_cell: str) -> Tuple[str, str]:
        """
        Return primary and secondary location of `which_cell` relative to the other cell in the pair
        If `which_cell` is the largest of the two or both cells are of the same size, secondary location is NA

        :param which_cell: REFERENCE or NEIGH
        """
        # preparations
        if which_cell == REFERENCE:
            cell_to_locate = self.reference_cell
            other_cell = self.neigh_cell
        elif which_cell == NEIGH:
            cell_to_locate = self.neigh_cell
            other_cell = self.reference_cell
        else:
            raise ValueError(f"Argument 'which_cell' must be '{REFERENCE}' or '{NEIGH}'")

        # primary location
        primary_location = None
        for where in [TOP, RIGHT]:
            if self.neigh_cell in self.reference_cell.neigh_cells[where]:
                primary_location = where if which_cell == NEIGH else OPPOSITE[where]
                break
        if not primary_location:
            raise ValueError("Could determine primary location with given arguments")

        # secondary location
        if cell_to_locate.width >= other_cell.width:
            secondary_location = NA
        elif primary_location in [LEFT, RIGHT]:
            if self.bottom_aligned and self.top_aligned:
                secondary_location = NA
            elif self.bottom_aligned:
                secondary_location = BOTTOM
            elif self.top_aligned:
                secondary_location = TOP
            else:
                raise ValueError("Could not locate with given arguments")
        elif primary_location in [TOP, BOTTOM]:
            if self.left_aligned and self.right_aligned:
                secondary_location = NA
            elif self.left_aligned:
                secondary_location = LEFT
            elif self.right_aligned:
                secondary_location = RIGHT
            else:
                raise ValueError("Could not locate with given arguments")
        else:
            raise ValueError("Could not locate with given arguments")
        return primary_location, secondary_location

    def smallest(self) -> Union[Cell, None]:
        """
        Returns the smallest cell of self.`reference_cell` and self.`neigh_cell` or None if cells have the same width
        """
        if self.reference_cell.width < self.neigh_cell.width:
            return self.reference_cell
        elif self.reference_cell.width > self.neigh_cell.width:
            return self.neigh_cell
        else:
            return None

    def transform(
            self,
            pos: Union[Tuple[int, int], np.ndarray],
            from_array,
            to_array
    ) -> Union[Tuple[int, int], np.ndarray]:
        """
        Transforms pixel position from one array to another

        :param pos: pixel position (numpy array index) that should be transformed. must be a tuple of 2 ints or a numpy
        array with row 0 = row index and row 1 = col index
        :param from_array: 'reference', 'neigh', or 'merged'
        :param to_array: 'reference', 'neigh' or 'merged'
        """
        if from_array == REFERENCE and to_array == MERGED:
            shift = [self.reference_cell_shift[0], self.reference_cell_shift[1]]
        if from_array == MERGED and to_array == REFERENCE:
            shift = np.array([self.reference_cell_shift[0], self.reference_cell_shift[1]]) * -1
        if from_array == NEIGH and to_array == MERGED:
            shift = [self.neigh_cell_shift[0], self.neigh_cell_shift[1]]
        if from_array == MERGED and to_array == NEIGH:
            shift = np.array([self.neigh_cell_shift[0], self.neigh_cell_shift[1]]) * -1
        if isinstance(pos, tuple):
            pos = np.array(pos)
            return tuple(pos + shift)
        elif isinstance(pos, np.ndarray):
            return (pos.T + shift).T

    def maxima(self) -> Dict[str, List[Tuple[int, int]]]:
        """
        Return a dict of right-hand-side and left-hand-side indices of maximum locations (cell pair coordinates)
        {rhs: [maxima], lhs: [maxima]}.
        \n
        Only maxima higher than `min_obstacle_height` - `search_precision` are included.
        """
        if self.neigh_primary_location == RIGHT:
            # right-hand-side edges are BOTTOM
            if self.bottom_aligned:
                # Calculate maxima in the continuous string of values at this side of the cell pair
                rhs_pixels = np.hstack([
                    self.reference_cell.edge_pixels(BOTTOM),
                    self.neigh_cell.edge_pixels(BOTTOM)
                ])
                rhs_maxima_1d, _ = find_peaks(rhs_pixels, prominence=self.ld.min_peak_prominence)
                row_indices = np.ones(rhs_maxima_1d.shape) * (self.height - 1)
                rhs_maxima = np.vstack([row_indices, rhs_maxima_1d]).T.astype(int)

            else:
                # Calculate maxima in each cell separately and stack them
                ref_maxima = self.reference_cell.maxima(BOTTOM)
                ref_maxima_transformed = np.array([self.transform(i, REFERENCE, MERGED) for i in ref_maxima])
                neigh_maxima = self.neigh_cell.maxima(BOTTOM)
                neigh_maxima_transformed = np.array([self.transform(i, NEIGH, MERGED) for i in neigh_maxima])
                rhs_maxima = np.array(ref_maxima_transformed.tolist() + neigh_maxima_transformed.tolist())

            # left-hand-side edges are TOP
            if self.top_aligned:
                # Calculate maxima in the continuous string of values at this side of the cell pair
                lhs_pixels = np.hstack([
                    self.reference_cell.edge_pixels(TOP),
                    self.neigh_cell.edge_pixels(TOP)
                ])
                lhs_maxima_1d, _ = find_peaks(lhs_pixels, prominence=self.ld.min_peak_prominence)
                row_indices = np.zeros(lhs_maxima_1d.shape)
                lhs_maxima = np.vstack([row_indices, lhs_maxima_1d]).T.astype(int)

            else:
                # Calculate maxima in each cell separately and stack them
                ref_maxima = self.reference_cell.maxima(TOP)
                ref_maxima_transformed = np.array([self.transform(i, REFERENCE, MERGED) for i in ref_maxima])
                neigh_maxima = self.neigh_cell.maxima(TOP)
                neigh_maxima_transformed = np.array([self.transform(i, NEIGH, MERGED) for i in neigh_maxima])
                lhs_maxima = np.array(ref_maxima_transformed.tolist() + neigh_maxima_transformed.tolist())

        elif self.neigh_primary_location == TOP:
            # right-hand-side edges are RIGHT
            if self.right_aligned:
                # Calculate maxima in the continuous string of values at this side of the cell pair
                rhs_pixels = np.hstack([
                    self.neigh_cell.edge_pixels(RIGHT),
                    self.reference_cell.edge_pixels(RIGHT)
                ])
                rhs_maxima_1d, _ = find_peaks(rhs_pixels, prominence=self.ld.min_peak_prominence)
                col_indices = np.ones(rhs_maxima_1d.shape) * (self.width - 1)
                rhs_maxima = np.vstack([rhs_maxima_1d, col_indices]).T.astype(int)

            else:
                # Calculate maxima in each cell separately and stack them
                ref_maxima = self.reference_cell.maxima(RIGHT)
                ref_maxima_transformed = np.array([self.transform(i, REFERENCE, MERGED) for i in ref_maxima])
                neigh_maxima = self.neigh_cell.maxima(RIGHT)
                neigh_maxima_transformed = np.array([self.transform(i, NEIGH, MERGED) for i in neigh_maxima])
                rhs_maxima = np.array(neigh_maxima_transformed.tolist() + ref_maxima_transformed.tolist())

            # left-hand-side edges are LEFT
            if self.left_aligned:
                # Calculate maxima in the continuous string of values at this side of the cell pair
                lhs_pixels = np.hstack([
                    self.neigh_cell.edge_pixels(LEFT),
                    self.reference_cell.edge_pixels(LEFT),
                ])
                lhs_maxima_1d, _ = find_peaks(lhs_pixels, prominence=self.ld.min_peak_prominence)
                col_indices = np.zeros(lhs_maxima_1d.shape)
                lhs_maxima = np.vstack([lhs_maxima_1d, col_indices]).T.astype(int)

            else:
                # Calculate maxima in each cell separately and stack them
                ref_maxima = self.reference_cell.maxima(LEFT)
                ref_maxima_transformed = np.array([self.transform(i, REFERENCE, MERGED) for i in ref_maxima])
                neigh_maxima = self.neigh_cell.maxima(LEFT)
                neigh_maxima_transformed = np.array([self.transform(i, NEIGH, MERGED) for i in neigh_maxima])
                lhs_maxima = np.array(neigh_maxima_transformed.tolist() + ref_maxima_transformed.tolist())

        else:
            raise ValueError(f"self.neigh_primary_location = {self.neigh_primary_location}")

        # Filter out maxima with too low pixel values
        filtered_rhs_maxima = []
        for pos in rhs_maxima:
            pos = tuple(pos)
            pixel_value = self.pixels[pos]
            if pixel_value > self.lowest_edge.exchange_level + \
                    self.ld.min_obstacle_height - \
                    self.ld.search_precision:
                filtered_rhs_maxima.append(pos)

        filtered_lhs_maxima = []
        for pos in lhs_maxima:
            pos = tuple(pos)
            pixel_value = self.pixels[pos]
            if pixel_value > self.lowest_edge.exchange_level + \
                    self.ld.min_obstacle_height - \
                    self.ld.search_precision:
                filtered_lhs_maxima.append(pos)

        return {RIGHTHANDSIDE: filtered_rhs_maxima, LEFTHANDSIDE: filtered_lhs_maxima}

    def crest_level_from_pixels(
            self,
            pixels: np.ndarray,
            from_pos: Tuple[int, int],
            to_pos: Tuple[int, int]
    ) -> Union[float, None]:
        """
        Find obstacle in `pixels` and return its crest level

        Returns None if no obstacle is found
        """
        from_val = pixels[from_pos]
        to_val = pixels[to_pos]

        # case: flat(ish) cellpair (from_val or max_to_val is not significantly higher than the lowest pixel)
        if np.nanmin([from_val, to_val]) - np.nanmin(pixels) < self.ld.search_precision:
            return None

        # now find the obstacle crest level iteratively
        hmin = np.nanmin(pixels)
        hmax = np.nanmax([from_val, to_val])

        # case: from and to positions already connect at hmax
        labelled_pixels, labelled_pixels_nr_features = label(pixels >= hmax, structure=SEARCH_STRUCTURE)
        from_pixel_label = int(labelled_pixels[from_pos])
        to_pixel_label = labelled_pixels[to_pos]
        if from_pixel_label != 0 and np.any(to_pixel_label == from_pixel_label):
            obstacle_crest_level = hmax

        # all other cases
        else:
            while (hmax - hmin) > self.ld.search_precision:
                hcurrent = np.nanmean([hmin, hmax])
                labelled_pixels, _ = label(pixels > hcurrent, structure=SEARCH_STRUCTURE)
                from_pixel_label = int(labelled_pixels[from_pos])
                to_pixel_label = labelled_pixels[to_pos]
                if from_pixel_label != 0 and np.any(to_pixel_label == from_pixel_label):
                    # the two sides are connected at this threshold
                    hmin = hcurrent
                else:
                    # the two sides are NOT connected at this threshold
                    hmax = hcurrent

            obstacle_crest_level = float(np.mean([hmin, hmax]))

        return obstacle_crest_level

    @staticmethod
    def squash_indices(array_a: np.ndarray, array_b: np.ndarray, side: str, secondary_location: Union[str, None]):
        """
        Return the indices of the active pixels at `side` in a CellPair
        If side is TOP or BOTTOM, secondary location must be LEFT or RIGHT
        If side is LEFT or RIGHT, secondary location must be TOP or BOTTOM
        Value 'N/A' for secondary_location will be treated as None
        """
        secondary_location = None if secondary_location == NA else secondary_location
        if secondary_location:
            if array_a.shape[1] > array_b.shape[1]:
                smallest = array_b.astype(float)
                largest = array_a.astype(float)
            elif array_a.shape[1] < array_b.shape[1]:
                smallest = array_a.astype(float)
                largest = array_b.astype(float)
            else:
                raise ValueError(
                    f"secondary_location is '{secondary_location}' (i.e., not None), but arrays have the same shape"
                )
            if secondary_location in (LEFT, TOP):
                pad_width = ((0, 0), (0, smallest.shape[1]))  # (rows before, rows after), (cols before, cols after)
            elif secondary_location in (RIGHT, BOTTOM):
                pad_width = ((0, 0), (smallest.shape[1], 0))  # (rows before, rows after), (cols before, cols after)
            smallest_padded = np.pad(smallest, pad_width=pad_width, mode='constant', constant_values=np.nan)
            arrays_to_aggregate = [smallest_padded, largest]
        else:
            if array_a.shape != array_b.shape:
                raise ValueError(
                    "secondary_location is 'NA' or None, but arrays do not have the same shape"
                )
            arrays_to_aggregate = [array_a.astype(float), array_b.astype(float)]

        if side in [RIGHT, BOTTOM]:
            aggregate = np.nanmax
        elif side in [LEFT, TOP]:
            aggregate = np.nanmin

        return aggregate(arrays_to_aggregate, axis=0).astype(int)

    def side_indices(self, side):
        """
        Return numpy array of indices for pixels at `side`
        """
        reference_indices = self.transform(
            self.reference_cell.side_indices(side),
            from_array=REFERENCE,
            to_array=MERGED
        )

        neigh_indices = self.transform(
            self.neigh_cell.side_indices(side),
            from_array=NEIGH,
            to_array=MERGED
        )
        if self.reference_secondary_location != NA:
            secondary_location = self.reference_secondary_location
        else:
            secondary_location = self.neigh_secondary_location
        return self.squash_indices(reference_indices, neigh_indices, side=side, secondary_location=secondary_location)

    def find_obstacles(self):
        """
        Obstacles are identified and assigned to the appropriate Edge
        """
        maxima = self.maxima()
        for from_pos in maxima[LEFTHANDSIDE]:
            for to_pos in maxima[RIGHTHANDSIDE]:
                from_pos_cell = self.locate_pos(from_pos)
                from_pos_transformed = self.transform(pos=from_pos, from_array=MERGED, to_array=from_pos_cell)
                to_pos_cell = self.locate_pos(to_pos)
                to_pos_transformed = self.transform(pos=to_pos, from_array=MERGED, to_array=to_pos_cell)
                if from_pos_cell == to_pos_cell:
                    # find obstacle in that cell
                    cell_or_cell_pair = self.cells[from_pos_cell]
                    from_pos_arg = from_pos_transformed
                    to_pos_arg = to_pos_transformed
                else:
                    # find obstacle in the cell pair
                    cell_or_cell_pair = self
                    from_pos_arg = from_pos
                    to_pos_arg = to_pos
                pixels = cell_or_cell_pair.pixels
                crest_level = self.crest_level_from_pixels(
                    pixels=pixels,
                    from_pos=from_pos_arg,
                    to_pos=to_pos_arg
                )
                if crest_level is None:
                    continue
                # check if obstacle is relevant
                # for "one cell" obstacles, base this check on the pixels in that cell only
                if not is_obstacle_relevant(
                        cell_or_cellpair=cell_or_cell_pair,
                        pixels=pixels,
                        crest_level=crest_level,
                        from_pos=from_pos_arg,
                        compare_to_sides=[self.reference_primary_location, self.neigh_primary_location]
                ):
                    continue
                # determine other obstacle properties
                # # from_edges, to_edges, from_cell, to_cell, from_pos, to_pos
                if self.neigh_primary_location == TOP:
                    from_side = LEFT
                    to_side = RIGHT
                else:
                    from_side = TOP
                    to_side = BOTTOM
                from_cell = self.cells[from_pos_cell]
                to_cell = self.cells[to_pos_cell]

                obstacle = Obstacle(
                    ld=self.ld,
                    crest_level=crest_level,
                    from_side=from_side,
                    to_side=to_side,
                    from_cell=from_cell,
                    to_cell=to_cell,
                    from_pos=from_pos_transformed,
                    to_pos=to_pos_transformed
                )

                # # edge
                # edges are all whose flowline is intersected by the obstacle, except the from_edge and to_edge
                potential_edges = []
                for cell in self.cells.values():
                    for side in [TOP, RIGHT, BOTTOM, LEFT]:
                        for edge in cell.edges(side):
                            if edge not in [obstacle.from_edge, obstacle.to_edge] + potential_edges:
                                potential_edges.append(edge)
                edges = [pe for pe in potential_edges if pe.flowline_geometry.intersects(obstacle.geometry)]
                if len(edges) == 0:
                    continue  # this can happen e.g. at the model boundary in some cases; there is an obstacle, but it
                    # doesn't intersect any relevant flowlines
                # assign obstacle to crossing edges (and v.v.) if they are high enough
                for edge in edges:
                    if crest_level > edge.exchange_level + \
                            self.ld.min_obstacle_height - \
                            self.ld.search_precision:
                        edge.obstacles.append(obstacle)
                        obstacle.edges.append(edge)

    def find_connecting_obstacles(self):
        """
        Assumes that 'normal' obstacles have already been found

        If a high line element in the DEM is slightly skewed relative to the grid, the obstacles it produces may
        contain a gap at the location where it switches sides. This method generates an obstacle that connects the
        two sides, e.g.:

            |                   |
            |         --->      |
            |         --->      |___
                |     --->          |
                |                   |
                |                   |
        """
        middle_edge = self.edges[1][0]

        if self.neigh_primary_location == TOP:
            lhs = LEFT
            rhs = RIGHT
        else:
            lhs = TOP
            rhs = BOTTOM

        lhs_edge_1 = self.reference_cell.edges(lhs, -1)
        lhs_edge_2 = self.neigh_cell.edges(lhs, 0)
        rhs_edge_1 = self.reference_cell.edges(rhs, -1)
        rhs_edge_2 = self.neigh_cell.edges(rhs, 0)

        for lhs_edge, rhs_edge in [(lhs_edge_1, rhs_edge_2), (lhs_edge_2, rhs_edge_1)]:
            if lhs_edge and rhs_edge:
                for lhs_obstacle in lhs_edge.obstacles:
                    for rhs_obstacle in rhs_edge.obstacles:
                        # find the position of the lhs_obstacle on the middle edge
                        if lhs_obstacle.from_edge == middle_edge:
                            lhs_pos = lhs_obstacle.from_pos
                            lhs_cell = REFERENCE if lhs_obstacle.from_cell == self.reference_cell else NEIGH
                        elif lhs_obstacle.to_edge == middle_edge:
                            lhs_pos = lhs_obstacle.to_pos
                            lhs_cell = REFERENCE if lhs_obstacle.to_cell == self.reference_cell else NEIGH
                        else:
                            continue
                        lhs_pos_in_cell_pair = self.transform(pos=lhs_pos, from_array=lhs_cell, to_array=MERGED)

                        # find the position of the rhs_obstacle on the middle edge
                        if rhs_obstacle.from_edge == middle_edge:
                            rhs_pos = rhs_obstacle.from_pos
                            rhs_cell = REFERENCE if rhs_obstacle.from_cell == self.reference_cell else NEIGH
                        elif rhs_obstacle.to_edge == middle_edge:
                            rhs_pos = rhs_obstacle.to_pos
                            rhs_cell = REFERENCE if rhs_obstacle.to_cell == self.reference_cell else NEIGH
                        else:
                            continue
                        rhs_pos_in_cell_pair = self.transform(pos=rhs_pos, from_array=rhs_cell, to_array=MERGED)

                        # connect lhs_pos and rhs_pos. If possible @ sufficient height, obstacle is added to middle edge
                        crest_level = self.crest_level_from_pixels(
                            pixels=self.pixels,
                            from_pos=lhs_pos_in_cell_pair,
                            to_pos=rhs_pos_in_cell_pair
                        )
                        if crest_level:
                            if crest_level > middle_edge.exchange_level + \
                                    self.ld.min_obstacle_height - \
                                    self.ld.search_precision:
                                obstacle = Obstacle(
                                    ld=self.ld,
                                    crest_level=crest_level,
                                    from_cell=self.cells[lhs_cell],
                                    to_cell=self.cells[rhs_cell],
                                    from_pos=lhs_pos,
                                    to_pos=rhs_pos,
                                    edges=[middle_edge]
                                )
                                obstacle.from_edge = middle_edge
                                obstacle.to_edge = middle_edge
                                middle_edge.obstacles.append(obstacle)


def is_obstacle_relevant(
        cell_or_cellpair: Union[Cell, CellPair],
        pixels: np.ndarray,
        crest_level: float,
        from_pos: Tuple[int, int],
        compare_to_sides: List
):
    """
    Example:
        - obstacle runs from left to right
        - crest level = 10
        - all pixels at bottom edge of bottom cell >= 10
        - case A: the obstacle pixels ARE connected to the bottom edge pixels at (10 - min_obstacle_height)
        - outcome: obstacle IS NOT relevant
        - case B: the obstacle pixels ARE NOT connected to the bottom edge pixels at (10 - min_obstacle_height)
        - outcome: obstacle IS relevant

    >>>
    case_a = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 10, 10, 10, 10, 10],
            [0, 0, 0, 0, 0, 10, 10, 0, 0, 0, 0],
            [0, 0, 0, 0, 10, 0, 10, 0, 0, 0, 0],
            [0, 0, 0, 10, 10, 10, 0, 0, 0, 0, 0],
            [0, 10, 10, 0, 0, 0, 0, 0, 0, 0, 0],
            [10, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        ]
    )

    >>>
    case_b = np.array(
        [
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 10, 10, 10, 10, 10],
            [0, 0, 0, 0, 0, 10, 10, 0, 0, 0, 0],
            [0, 10, 10, 10, 10, 0, 10, 0, 0, 0, 0],
            [10, 10, 10, 10, 10, 10, 0, 0, 0, 0, 0],
            [0, 0, 10, 0, 0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            [10, 10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
        ]
    )

    """
    labelled_pixels = label(
        pixels >= crest_level - cell_or_cellpair.ld.min_obstacle_height,
        structure=SEARCH_STRUCTURE
    )[0]
    from_pos_label = labelled_pixels[from_pos]
    relevant = True
    for side in compare_to_sides:
        indices = cell_or_cellpair.side_indices(side)
        side_labels = labelled_pixels[indices[0], indices[1]]
        if np.all(side_labels == from_pos_label):
            relevant = False
            break
    return relevant


def highest(elements: List[Union[Obstacle, Edge]]):
    """
    Return the highest element from a list of obstacles or edges.
    """
    max_element_height = -PSEUDO_INFINITE
    highest_element = None
    for element in elements:
        attr_name = 'exchange_level' if isinstance(element, Edge) else 'crest_level'
        if getattr(element, attr_name) >= max_element_height:
            max_element_height = getattr(element, attr_name)
            highest_element = element
    return highest_element


def lowest(elements: List[Union[Obstacle, Edge]]):
    """
    Return the lowest element from a list of obstaclesor edges.
    """
    min_element_height = PSEUDO_INFINITE
    lowest_element = None
    for element in elements:
        attr_name = 'exchange_level' if isinstance(element, Edge) else 'crest_level'
        if getattr(element, attr_name) <= min_element_height:
            min_element_height = getattr(element, attr_name)
            lowest_element = element
    return lowest_element
