# (c) Nelen & Schuurmans, see LICENSE.rst.

from collections import OrderedDict
from copy import copy
import datetime
import logging

from osgeo import gdal
from osgeo import ogr
from osgeo import osr
from sqlalchemy.orm import load_only

from qgis.core import Qgis

from threedi_results_analysis.processing.deps.sql_models.constants import Constants
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import BoundaryCondition1D
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import ConnectionNode
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import CrossSectionDefinition
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import ImperviousSurface
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import ImperviousSurfaceMap
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Manhole
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Orifice
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Pipe
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Pumpstation
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Weir
from threedi_results_analysis.processing.deps.sufhyd.sufhyd_importer import SufhydReader
from threedi_results_analysis.utils.user_messages import messagebar_message
from threedi_schema import errors

logger = logging.getLogger(__name__)


def transform(wkt, srid_source, srid_dest):
    source_crs = osr.SpatialReference()
    source_crs.ImportFromEPSG(srid_source)
    dest_crs = osr.SpatialReference()
    dest_crs.ImportFromEPSG(srid_dest)
    if int(gdal.__version__[0]) >= 3:
        source_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
        dest_crs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    transformation = osr.CoordinateTransformation(source_crs, dest_crs)

    point = ogr.CreateGeometryFromWkt(wkt)
    point.Transform(transformation)
    return point.ExportToWkt()


class DataImportLogger(object):
    def __init__(self):
        pass
        self.log_tree = OrderedDict()

        self.level_count = dict()

    def add(self, level, base_msg, base_params, specific_msg, specific_params):

        if level not in self.level_count:
            self.level_count[level] = 0
        self.level_count[level] += 1

        if base_msg not in self.log_tree:
            self.log_tree[base_msg] = OrderedDict()

        msg = logging.getLevelName(level) + ": " + base_msg.format(**base_params)

        if msg not in self.log_tree[base_msg]:
            self.log_tree[base_msg][msg] = list()

        self.log_tree[base_msg][msg].append(specific_msg.format(**specific_params))

    def get_summary(self):
        return self.get_full_log(True)

    def get_full_log(self, only_main_items=False):

        txt = ""
        for main_key, main_item in list(self.log_tree.items()):
            for key, list_issues in list(main_item.items()):
                txt += key + " ({0} times)\n".format(len(list_issues))
                if not only_main_items:
                    for issue in list_issues:
                        txt += "    %s\n" % issue

        return txt


class Importer(object):
    def __init__(self, import_file, threedi_database):
        self.import_file = import_file
        self.file_type = "sufhyd"
        self.db = threedi_database

        self.logging_tree = OrderedDict()
        self.log = DataImportLogger()

    def is_db_valid(self):
        schema = self.db.schema
        try:
            schema.validate_schema()
        except errors.MigrationMissingError:
            messagebar_message(
                title="sufhyd import",
                msg=(
                    "The selected 3Di spatialite does not have the latest "
                    "database schema version. Please migrate this spatialite and "
                    "try again: Processing > Toolbox > 3Di > Schematisation > "
                    "Migrate spatialite"
                ),
                level=Qgis.Warning
            )
            return False
        return True

    def run_import(self):
        """
        main function for performing all import tasks
        """
        if not self.is_db_valid():
            return

        # self.db.create_and_check_fields()

        if self.file_type == "sufhyd":
            logger.info("load sufhyd data")
            data = self.load_sufhyd_data()
            logger.info("check import data")
            self.check_import_data(data)
            logger.info("transform import data")
            self.transform_import_data(data)
            logger.info("write data to db")
            commit_counts = self.write_data_to_db(data)

            logger.warning("Summary of import:\n" + self.log.get_summary())

            # write logging to file
            log_file = open(self.import_file + ".log", "w")
            log_file.write(
                "Import on {0} of file: {1}.\n".format(
                    datetime.datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                    self.import_file,
                )
            )

            log_file.write(
                "Added to spatialite at {0} :\n".format(
                    self.db.path
                )
            )
            log_file.write(
                "{profiles} profiles\n"
                "{manholes} manholes\n"
                "{pipes} pipes\n"
                "{structures} structures"
                "{outlets} outlets\n"
                "{impervious_surfaces} impervious surfaces\n"
                "".format(**commit_counts)
            )

            log_file.write(self.log.get_full_log())
            log_file.close()

            msg = (
                "{errors} errors and {warnings} warnings, see qgis log for "
                "the summary and {log_file.name} for the full log".format(
                    errors=self.log.level_count.get(logging.ERROR, 0),
                    warnings=self.log.level_count.get(logging.WARNING, 0),
                    log_file=log_file,
                )
            )

            logger.info("sufhyd import ready = " + msg)

    def load_sufhyd_data(self):
        reader = SufhydReader(open(self.import_file, "r").read(), data_log=self.log)
        unused_fields = reader.parse_input()

        for ide_rec, unused_list in list(unused_fields.items()):
            for field, count in list(unused_list.items()):

                self.log.add(
                    logging.WARNING,
                    "Some fields provided in the sufhyd for object "
                    "'{ide_rec}' are not used.",
                    {"ide_rec": ide_rec},
                    "Data of '{ide_rec}' field '{field}' {count} times ignored.",
                    {"ide_rec": ide_rec, "field": field, "count": count},
                )

        return reader.get_data()

    def _check_on_unique(
        self,
        records,
        unique_field,
        remove_doubles=False,
        item_name_for_logging="",
        log_level=logging.WARNING,
    ):

        values = [m[unique_field] for m in records]

        if len(set(values)) == len(values):
            return True, set()

        doubles = []
        value_set = set()
        for i in reversed(list(range(0, len(records)))):
            record = records[i]
            if record[unique_field] in value_set:
                doubles.append(record)
                self.log.add(
                    log_level,
                    "double values in {unique_field} of {item_name_for_logging}",
                    {
                        "unique_field": unique_field,
                        "item_name_for_logging": item_name_for_logging,
                    },
                    "for records with {unique_field}: {code}",
                    {"unique_field": unique_field, "code": record[unique_field]},
                )

                if remove_doubles:
                    records.remove(record)
            else:
                value_set.add(record[unique_field])

        return False, doubles

    def check_import_data(self, data):

        self._check_on_unique(data["manholes"], "code", True, "knoop")
        self._check_on_unique(
            data["storage"], "node.code", True, "bergend oppervlak knoop"
        )
        self._check_on_unique(data["outlets"], "node.code", True, "uitlaat knoop")

        self._check_on_unique(data["weirs"], "code", False, "overstort")
        self._check_on_unique(data["pumpstations"], "code", False, "gemaal")
        self._check_on_unique(data["orifices"], "code", False, "doorlaat")

    def check_on_outlet_connections(self, data):

        outlet_dict = {c["node.code"]: c for c in data["outlets"]}
        manhole_dict = {m["code"]: m for m in data["manholes"]}
        used_outlets = {}

        # check on multiple connections
        for objects in (
            data["pipes"],
            data["pumpstations"],
            data["weirs"],
            data["orifices"],
        ):
            for obj in objects:
                for node in ("start_node.code", "end_node.code"):
                    code = obj[node]
                    if code in outlet_dict:
                        if code in used_outlets:
                            used_outlets[code] += 1

                            # add extra manhole
                            new_manhole = copy(manhole_dict[code])
                            new_manhole["code"] = (
                                new_manhole["code"] + "-" + str(used_outlets[code])
                            )

                            geom = new_manhole["geom"]
                            new_manhole["geom"] = (geom[0], geom[1] + 1.0, geom[2])
                            data["manholes"].append(new_manhole)

                            # redirect object to new manhole
                            obj[node] = new_manhole["code"]

                            # add extra outlet
                            new_outlet = copy(outlet_dict[code])
                            new_outlet["node.code"] = new_manhole["code"]
                            data["outlets"].append(new_outlet)

                            self.log.add(
                                logging.INFO,
                                "multiple connection to outlet",
                                {},
                                "multiple connection to outlet {orig_code}, "
                                "added extra manhole and outlet {new_code}",
                                {"orig_code": code, "new_code": new_manhole["code"]},
                            )

                        else:
                            used_outlets[code] = 1
        # 0
        not_connected_outlets = [
            outl for cod, outl in list(outlet_dict.items()) if cod not in used_outlets
        ]

        if len(not_connected_outlets) > 0:
            data["outlets"] = [
                outlet
                for outlet in data["outlets"]
                if outlet not in not_connected_outlets
            ]
            for outlet in not_connected_outlets:
                self.log.add(
                    logging.WARNING,
                    "no connection to outlet",
                    {},
                    "no connection to outlet {code}, outlet removed",
                    {"code": outlet["node.code"]},
                )

    def transform_import_data(self, data):

        self.check_on_outlet_connections(data)

        profiles = dict()
        profiles["default"] = {
            "width": 1,
            "height": 1,
            "shape": Constants.SHAPE_ROUND,
            "code": "default",
        }

        for obj_type in ["pipes", "orifices", "weirs"]:
            objects = data[obj_type]
            for obj in objects:
                crs = obj["cross_section_details"]
                if crs["shape"] == Constants.SHAPE_ROUND:
                    code = "round_{width}".format(**crs)
                elif crs["shape"] == Constants.SHAPE_EGG:
                    code = "egg_w{width}_h{height}".format(**crs)
                elif crs["shape"] == Constants.SHAPE_RECTANGLE:
                    if crs["height"] is None:
                        code = "rectangle_w{width}_open".format(**crs)
                    else:
                        code = "rectangle_w{width}_h{height}".format(**crs)
                else:
                    code = "default"

                # add unique profiles to profile definition
                if code not in profiles:
                    profiles[code] = crs
                    profiles[code]["code"] = code

                obj["crs_code"] = code

        # generate extra boundary nodes if needed
        manhole_geom = {m["code"]: m["geom"] for m in data["manholes"]}
        inc_nr = 1
        for obj_type in ["orifices", "weirs"]:
            objects = data[obj_type]
            for obj in objects:
                if obj["end_node.code"] is None:
                    # add extra node with boundary conditions
                    bound_code = obj["code"] + "-bound" + str(inc_nr)
                    inc_nr += 1

                    geom = manhole_geom.get(obj["start_node.code"], (0.0, 0.0, 28992))
                    new_geom = (geom[0], geom[1] + 1.0, geom[2])

                    data["manholes"].append(
                        {
                            "code": bound_code,
                            "display_name": bound_code,
                            "width": 1.0,
                            "length": 1.0,
                            "shape": Constants.MANHOLE_SHAPE_SQUARE,
                            "bottom_level": obj["crest_level"] - 1.0,
                            "surface_level": obj["crest_level"] + 1.0,
                            "geom": new_geom,
                        }
                    )
                    obj["end_node.code"] = bound_code

                    if (
                        obj_type == "orifice"
                        or "boundary_details" not in obj
                        or obj["boundary_details"]["timeseries"] is None
                    ):
                        if obj["crest_level"] is not None:
                            waterlevel = obj["crest_level"] - 0.5
                        else:
                            waterlevel = -999.0
                        timeseries = "0,{0}/n9999,{0}".format(waterlevel)
                    else:
                        timeseries = obj["boundary_details"]["timeseries"]

                    data["outlets"].append(
                        {
                            "node.code": bound_code,
                            "boundary_type": Constants.BOUNDARY_TYPE_WATERLEVEL,
                            "timeseries": timeseries,
                        }
                    )

        # link_node_conversion
        link_dict = {k["end_node.code"]: k["start_node.code"] for k in data["links"]}

        storage_dict = {k["node.code"]: k for k in data["storage"]}

        # remove manholes which are part of a link
        data["manholes"] = [m for m in data["manholes"] if m["code"] not in link_dict]

        for manhole in data["manholes"]:
            # add storage area
            if manhole["code"] in storage_dict:
                manhole["storage_area"] = storage_dict[manhole["code"]]["storage_area"]
            else:
                manhole["storage_area"] = None

            # if manhole['code'] in link_dict:
            #     logger.info("delete manhole %s as part of a linkage." % manhole['code'])
            #     del manhole
            #     continue

        data["profiles"] = profiles

    def write_data_to_db(self, data):
        """
        writes data to model database

        data (dict): dictionary with for each object type a list of objects

        returns: (dict) with number of objects committed to the database of
                 each object type

        """

        commit_counts = {}

        session = self.db.get_session()

        crs_list = []
        for crs in list(data["profiles"].values()):
            crs_list.append(CrossSectionDefinition(**crs))

        commit_counts["profiles"] = len(crs_list)
        session.bulk_save_objects(crs_list)
        session.commit()

        crs_list = (
            session.query(CrossSectionDefinition)
            .options(
                load_only(
                    CrossSectionDefinition.id,
                    CrossSectionDefinition.code,
                )
            )
            .order_by(CrossSectionDefinition.id)
            .all()
        )
        crs_dict = {m.code: m.id for m in crs_list}
        del crs_list

        con_list = []
        srid = 4326

        for manhole in data["manholes"]:
            wkt = transform(
                "POINT({0} {1})".format(*manhole["geom"]), manhole["geom"][2], srid
            )
            con_list.append(
                ConnectionNode(
                    code=manhole["code"],
                    storage_area=manhole["storage_area"],
                    the_geom="srid={0};{1}".format(srid, wkt),
                )
            )

        session.bulk_save_objects(con_list)
        session.commit()

        con_list = (
            session.query(ConnectionNode)
            .options(load_only(ConnectionNode.id, ConnectionNode.code))
            .order_by(ConnectionNode.id)
            .all()
        )
        con_dict = {m.code: m.id for m in con_list}
        del con_list

        # add extra references for link nodes (one node, multiple linked codes
        for link in data["links"]:
            try:
                if link["end_node.code"] in con_dict:
                    con_dict[link["end_node.code"]] = con_dict[link["start_node.code"]]
                else:
                    con_dict[link["end_node.code"]] = con_dict[link["start_node.code"]]
            except KeyError:
                logger.exception("Node of link not found while adding extra references")
                self.log.add(
                    logging.ERROR,
                    "node of link not found in nodes",
                    {},
                    "start node {start_node} or end_node {end_node} of link "
                    "definition not found",
                    {
                        "start_node": link["start_node.code"],
                        "end_node": link["end_node.code"],
                    },
                )

        con_dict[None] = None
        con_dict[""] = None

        man_list = []
        for manhole in data["manholes"]:
            del manhole["geom"]
            del manhole["storage_area"]

            manhole["connection_node_id"] = con_dict[manhole["code"]]
            man_list.append(Manhole(**manhole))

        commit_counts["manholes"] = len(man_list)
        session.bulk_save_objects(man_list)
        session.commit()
        del man_list

        pipe_list = []
        for pipe in data["pipes"]:
            try:
                pipe["connection_node_start_id"] = con_dict[pipe["start_node.code"]]
            except KeyError:
                logger.exception("Start node of pipe not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "Start node of pipe not found in nodes",
                    {},
                    "Start node {start_node} of pipe with code {code} not found",
                    {"start_node": pipe["start_node.code"], "code": pipe["code"]},
                )

            try:
                pipe["connection_node_end_id"] = con_dict[pipe["end_node.code"]]
            except KeyError:
                logger.exception("End node of pipe not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "End node of pipe not found in nodes",
                    {},
                    "End node {end_node} of pipe with code {code} not found",
                    {"end_node": pipe["end_node.code"], "code": pipe["code"]},
                )

            pipe["cross_section_definition_id"] = crs_dict[pipe["crs_code"]]

            del pipe["start_node.code"]
            del pipe["end_node.code"]
            del pipe["crs_code"]
            del pipe["cross_section_details"]

            pipe_list.append(Pipe(**pipe))

        commit_counts["pipes"] = len(pipe_list)
        session.bulk_save_objects(pipe_list)
        session.commit()
        del pipe_list

        obj_list = []
        for pump in data["pumpstations"]:
            try:
                pump["connection_node_start_id"] = con_dict[pump["start_node.code"]]
            except KeyError:
                logger.exception("Start node of pump not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "Start node of pump not found in nodes",
                    {},
                    "Start node {start_node} of pump with code {code} not found",
                    {"start_node": pump["start_node.code"], "code": pump["code"]},
                )

            try:
                pump["connection_node_end_id"] = con_dict[pump["end_node.code"]]
            except KeyError:
                logger.exception("End node of pump not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "End node of pump not found in nodes",
                    {},
                    "End node {end_node} of pump with code {code} not found",
                    {"end_node": pump["end_node.code"], "code": pump["code"]},
                )

            del pump["start_node.code"]
            del pump["end_node.code"]

            obj_list.append(Pumpstation(**pump))

        for weir in data["weirs"]:
            try:
                weir["connection_node_start_id"] = con_dict[weir["start_node.code"]]
            except KeyError:
                logger.exception("Start node of weir not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "Start node of weir not found in nodes",
                    {},
                    "Start node {start_node} of weir with code {code} not found",
                    {"start_node": weir["start_node.code"], "code": weir["code"]},
                )

            try:
                weir["connection_node_end_id"] = con_dict[weir["end_node.code"]]
            except KeyError:
                logger.exception("End node of weir not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "End node of weir not found in nodes",
                    {},
                    "End node {end_node} of weir with code {code} not found",
                    {"end_node": weir["end_node.code"], "code": weir["code"]},
                )

            weir["cross_section_definition_id"] = crs_dict[weir["crs_code"]]

            del weir["start_node.code"]
            del weir["end_node.code"]
            del weir["crs_code"]
            del weir["cross_section_details"]
            del weir["boundary_details"]

            obj_list.append(Weir(**weir))

        for orif in data["orifices"]:
            try:
                orif["connection_node_start_id"] = con_dict[orif["start_node.code"]]
            except KeyError:
                logger.exception("Start node of orifice not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "Start node of orifice not found in nodes",
                    {},
                    "Start node {start_node} of orifice with code {code} not found",
                    {"start_node": orif["start_node.code"], "code": orif["code"]},
                )

            try:
                orif["connection_node_end_id"] = con_dict[orif["end_node.code"]]
            except KeyError:
                logger.exception("End node of orifice not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "End node of orifice not found in nodes",
                    {},
                    "End node {end_node} of orifice with code {code} not found",
                    {"end_node": orif["end_node.code"], "code": orif["code"]},
                )

            orif["cross_section_definition_id"] = crs_dict[orif["crs_code"]]

            del orif["start_node.code"]
            del orif["end_node.code"]
            del orif["crs_code"]
            del orif["cross_section_details"]

            obj_list.append(Orifice(**orif))

        commit_counts["structures"] = len(obj_list)
        session.bulk_save_objects(obj_list)
        session.commit()
        del obj_list

        # Outlets (must be saved after weirs, orifice, pumpstation, etc.
        # because of constraints)
        outlet_list = []
        for outlet in data["outlets"]:
            try:
                outlet["connection_node_id"] = con_dict[outlet["node.code"]]

                del outlet["node.code"]
                outlet_list.append(BoundaryCondition1D(**outlet))
            except KeyError:
                logger.exception("Node of outlet not found in nodes")
                self.log.add(
                    logging.ERROR,
                    "node of outlet not found in nodes",
                    {},
                    "node {node} of outlet definition not found",
                    {"node": outlet["node.code"]},
                )

        commit_counts["outlets"] = len(outlet_list)
        session.bulk_save_objects(outlet_list)
        session.commit()
        del outlet_list

        # Impervious surfaces
        imp_list = []
        for imp in data["impervious_surfaces"]:
            imp_list.append(ImperviousSurface(**imp))

        commit_counts["impervious_surfaces"] = len(imp_list)
        session.bulk_save_objects(imp_list)
        session.commit()

        imp_list = (
            session.query(ImperviousSurface)
            .options(load_only(ImperviousSurface.id, ImperviousSurface.code))
            .order_by(ImperviousSurface.id)
            .all()
        )
        imp_dict = {m.code: m.id for m in imp_list}
        del imp_list

        map_list = []
        for imp_map in data["impervious_surface_maps"]:
            try:
                imp_map["connection_node_id"] = con_dict[imp_map["node.code"]]
            except KeyError:
                logger.exception("Manhole connected to impervious surface not found")
                self.log.add(
                    logging.ERROR,
                    "Manhole connected to impervious surface not found",
                    {},
                    "Node {node} of impervious surface map connected to "
                    "impervious surface with code {code} not found",
                    {"node": imp_map["node.code"], "code": imp_map["imp_surface.code"]},
                )
                continue

            imp_map["impervious_surface_id"] = imp_dict[imp_map["imp_surface.code"]]
            del imp_map["node.code"]
            del imp_map["imp_surface.code"]

            map_list.append(ImperviousSurfaceMap(**imp_map))

        session.bulk_save_objects(map_list)
        session.commit()

        return commit_counts
