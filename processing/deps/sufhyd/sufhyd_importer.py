# (c) Nelen & Schuurmans, see LICENSE.rst.
from threedi_results_analysis.processing.deps.sql_models.constants import Constants
from threedi_results_analysis.processing.deps.sufhyd.turtleurbanclasses import (
    HydroObjectFactory,
)

import logging


logger = logging.getLogger(__name__)


def check_unsupported_fields(obj, *fields):
    unsupported_fields = []
    for field in fields:
        if getattr(obj, field, None) is not None:
            unsupported_fields.append(field)

    return unsupported_fields


shape_mapping = {
    None: None,
    "": None,
    "00": Constants.SHAPE_ROUND,
    "01": Constants.SHAPE_EGG,
    "02": Constants.SHAPE_RECTANGLE,
    "99": None,
}  # not supported in 3Di or in import: 03 - U-vorm, 04 - heul, 05 - muil en 06 - trapezium


manhole_shape_mapping = {
    "00": Constants.MANHOLE_SHAPE_SQUARE,
    "01": Constants.MANHOLE_SHAPE_ROUND,
    "02": Constants.MANHOLE_SHAPE_RECTANGLE,
}

material_mapping = {
    None: None,
    "": None,
    "00": Constants.MATERIAL_TYPE_CONCRETE,
    "01": Constants.MATERIAL_TYPE_PVC,
    "02": Constants.MATERIAL_TYPE_STONEWARE,
    "03": Constants.MATERIAL_TYPE_CAST_IRON,
    "04": Constants.MATERIAL_TYPE_BRICKWORK,
    "05": Constants.MATERIAL_TYPE_HPE,
    "06": Constants.MATERIAL_TYPE_HPDE,
    "07": Constants.MATERIAL_TYPE_SHEET_IRON,
    "08": Constants.MATERIAL_TYPE_STEEL,
}

pipe_type_mapping = {
    None: None,
    "": None,
    "00": Constants.SEWERAGE_TYPE_COMBINED,
    "01": Constants.SEWERAGE_TYPE_STORMWATER,
    "02": Constants.SEWERAGE_TYPE_WASTEWATER,
    "03": Constants.SEWERAGE_TYPE_TRANSPORT,
    "04": Constants.SEWERAGE_TYPE_OVERFLOW,
    "05": Constants.SEWERAGE_TYPE_SINKER,
    "06": Constants.SEWERAGE_TYPE_STORAGE,
    "07": Constants.SEWERAGE_TYPE_STORAGE_SETTLING_TANK,
}

surface_inclination_mapping = {
    "hel": Constants.SURFACE_INCLINATION_HELLEND,
    "vla": Constants.SURFACE_INCLINATION_VLAK,
    "vlu": Constants.SURFACE_INCLINATION_UITGESTREKT,
}

surface_class_mapping = {
    "gvh": Constants.SURFACE_CLASS_GESLOTEN_VERHARDING,
    "ovh": Constants.SURFACE_CLASS_OPEN_VERHARDING,
    "dak": Constants.SURFACE_CLASS_PAND,
    "onv": Constants.SURFACE_CLASS_ONVERHARD,
}


def get_value(value, value_type=None, default_value=None):
    if value is None or value == "":
        return default_value
    if value_type is not None:
        return value_type(value)
    return value


def multiply(value, multiplier, value_type=None, default_value=None):
    if value is None or value == "":
        return default_value
    if value_type is not None:
        value = value_type(value)
        return value_type(value * multiplier)
    return value * multiplier


def prettify(string):
    if string is None:
        return ""
    else:
        return str(string)


def get_code(geb_id1, id1, geb_id2=None, id2=None, post_fix=None, default_code=None):
    """
    Args:
        geb_id1 (string): area code
        id1(string): object id
        geb_id2(string): area code object 2
        id2(string): object id 2
        post_fix: addition at end of code
        default_code: returned value when id1 is None or ''

    Returns:
        (string): combined area code

    """
    if id1 is None or id1 == "":
        return default_code

    code = prettify(geb_id1) + "_" + prettify(id1)
    if id2 is not None and id2 != "":
        code += "-" + prettify(geb_id2) + "_" + prettify(id2)
    if post_fix is not None and post_fix != "":
        code += "-" + prettify(post_fix)
    return code


def point(x, y, srid_input=28992):

    return x, y, srid_input


class SufhydReader(object):
    """class loading sufhydfile"""

    def __init__(self, content_string, data_log):
        self.content_string = content_string
        self.active_object = None
        self.output = None
        self.errors = []
        self.log = data_log

    def get_hydro_objects(self):

        hydrofact = HydroObjectFactory()
        return hydrofact.hydroObjectListFromSUFHYD(self.content_string, self.log)

    def parse_input(self):
        """

        returns:

        """
        function_mapping = {
            "*KNP": self.parse_knoop,
            "*LEI": self.parse_leiding,
            "*GEM": self.parse_gemaal,
            "*OVS": self.parse_overstort,
            "*DRL": self.parse_doorlaat,
            "*UIT": self.parse_uitlaat,
            "*BOP": self.parse_bergend_oppervlak,
            # '*KOP': self.parse_koppeling,
            "*AFV": self.parse_afvoerend_oppervlak,
            "*KPG": self.parse_koppeling,
        }

        self.output = {
            "manholes": [],
            "pipes": [],
            "pumpstations": [],
            "weirs": [],
            "orifices": [],
            "outlets": [],
            "storage": [],
            "links": [],
            "impervious_surfaces": [],
            "impervious_surface_maps": [],
        }

        unused_fields = {key: dict() for key in list(function_mapping.keys())}

        for obj in self.get_hydro_objects():
            if hasattr(obj, "ide_rec"):
                # parse object
                if obj.ide_rec in function_mapping:
                    unused_fields_obj = function_mapping.get(obj.ide_rec, str)(obj)

                    # process unused fields for feedback to user

                    if unused_fields_obj is not None:
                        for field in unused_fields_obj:
                            if field not in unused_fields[obj.ide_rec]:
                                unused_fields[obj.ide_rec][field] = 0

                            unused_fields[obj.ide_rec][field] += 1

        return unused_fields

    def get_data(self):
        return self.output

    def get_shape(self, shape_code, record_code):
        shape = shape_mapping.get(shape_code)
        if shape is None:
            logger.warning("Unkown shape '%s' for record '%s'", shape_code, record_code)
            self.log.add(
                logging.WARNING,
                "Unknown profile shape in sufhyd record",
                {},
                "shape code '{shape}' for record with code {record_id}",
                {"shape": shape_code, "record_id": record_code},
            )
        return shape

    def get_manhole_shape(self, shape_code, record_code):
        manhole_shape = manhole_shape_mapping.get(shape_code)
        if manhole_shape is None:
            logger.warning(
                "Unkown manhole shape '%s' for record '%s'", shape_code, record_code
            )
            self.log.add(
                logging.WARNING,
                "Unknown manhole shape in sufhyd record",
                {},
                "shape code '{shape}' for record with code {record_id}",
                {"shape": shape_code, "record_id": record_code},
            )
        return manhole_shape

    def get_material_type(self, material_code, record_code):
        material_type = material_mapping.get(material_code)
        if material_type is None:
            logger.warning(
                "Unknown material '%s' for record '%s'", material_code, record_code
            )
            self.log.add(
                logging.WARNING,
                "Unknown material type in sufhyd record",
                {},
                "Material code '{material_code}' for record with code {record_id}",
                {"material_code": material_code, "record_id": record_code},
            )
        return material_type

    def get_sewerage_type(self, pipe_type_code, record_code):
        sewerage_type = pipe_type_mapping.get(pipe_type_code)
        if sewerage_type is None:
            logger.warning(
                "Unknown pipe type '%s' for record '%s'", pipe_type_code, record_code
            )
            self.log.add(
                logging.WARNING,
                "Unknown sewerage type in sufhyd record",
                {},
                "Sewarege type code '{pipe_type_code}' for record with code {record_id}",
                {"pipe_type_code": pipe_type_code, "record_id": record_code},
            )
        return sewerage_type

    def get_surface_class(self, surface_field_code):
        surface_class = surface_class_mapping.get(surface_field_code)
        if surface_class is None:
            logger.error("Unknown surface_class %s", surface_field_code)
        return surface_class

    def get_surface_inclination(self, surface_field_code):
        surface_inclination = surface_inclination_mapping.get(surface_field_code)
        if surface_inclination is None:
            logger.error("Unknown surface_class %s", surface_field_code)
        return surface_inclination

    @staticmethod
    def get_pipe_type(pipe_type_code):
        if pipe_type_code is None:
            return None
        else:
            return int(pipe_type_code)

    def add_object_error(self, error_type, message):

        self.errors.append(("input", error_type, message))

    def parse_knoop(self, knp):
        """parse knoop into manhole and impervious service

        :param knp:
        :return:
        """
        code = get_code(knp.ide_geb, knp.ide_knp)

        # get manhole attributes
        manhole = {
            "code": code,
            "display_name": code,
            "geom": point(
                multiply(knp.knp_xco, 0.001), multiply(knp.knp_yco, 0.001), 28992
            ),
            "surface_level": knp.mvd_niv,
            "width": knp.knp_bre,
            "length": knp.knp_len,
            "shape": self.get_manhole_shape(knp.knp_vrm, code),
            "bottom_level": knp.knp_bok,
            # 'material': self.get_material_type(knp.pro_mat),
        }

        self.output["manholes"].append(manhole)

        if knp.aan_inw is not None:
            drainage_area = {
                "code": code + "-inw",
                "surface_class": Constants.SURFACE_CLASS_PAND,
                "surface_inclination": Constants.SURFACE_INCLINATION_VLAK,
                "nr_of_inhabitants": knp.aan_inw,
                "area": 0,
            }
            self.output["impervious_surfaces"].append(drainage_area)

            imp_map = {
                "node.code": code,
                "imp_surface.code": code + "-inw",
                "percentage": 100,
            }
            self.output["impervious_surface_maps"].append(imp_map)

        return check_unsupported_fields(
            knp, "afv_vla", "afv_hel", "afv_vlu", "loz_con", "aan_won", "dwa_def"
        )

    def parse_leiding(self, leiding):

        code = get_code(
            leiding.ide_geb,
            leiding.ide_kn1,
            leiding.ide_gb2,
            leiding.ide_kn2,
            leiding.num_mvb,
        )

        pipe = {
            "code": code,
            "display_name": code,
            "start_node.code": get_code(leiding.ide_geb, leiding.ide_kn1),
            "end_node.code": get_code(leiding.ide_gb2, leiding.ide_kn2),
            "original_length": leiding.lei_len,
            "cross_section_details": {
                "shape": self.get_shape(leiding.pro_vrm, code),
                "width": leiding.pro_bre,
                "height": leiding.pro_hgt,
            },
            "invert_level_start_point": leiding.bob_kn1,
            "invert_level_end_point": leiding.bob_kn2,
            "sewerage_type": self.get_sewerage_type(leiding.lei_typ, code),
            "material": self.get_material_type(leiding.pro_mat, code),
        }  # not supported:

        if leiding.aan_inw is not None:
            drainage_area = {
                "code": code + "-inw",
                "surface_class": Constants.SURFACE_CLASS_PAND,
                "surface_inclination": Constants.SURFACE_INCLINATION_VLAK,
                "nr_of_inhabitants": leiding.aan_inw,
                "area": 0,
            }
            self.output["impervious_surfaces"].append(drainage_area)

            imp_map = {
                "node.code": pipe["start_node.code"],
                "imp_surface.code": code + "-inw",
                "percentage": 50,
            }
            self.output["impervious_surface_maps"].append(imp_map)

            imp_map = {
                "node.code": pipe["end_node.code"],
                "imp_surface.code": code + "-inw",
                "percentage": 50,
            }
            self.output["impervious_surface_maps"].append(imp_map)

        self.output["pipes"].append(pipe)

        return check_unsupported_fields(
            pipe,
            "pro_num",
            "afv_een",
            "afv_hel",
            "afv_vla",
            "afv_vlu",
            "pro_knw",
            "str_rch",
            "inv_kn1",
            "uit_kn1",
            "inv_kn2",
            "uit_kn2",
            "qdh_num",
            "qdh_niv",
            "nsh_frt",
            "nsh_frv",
            "dwa_def",
            "nsh_upt",
            "nsh_upn",
        )

    def parse_gemaal(self, gemaal):

        for i in range(1, 10):
            if type(getattr(gemaal, "pmp_af%i" % i, "")) is float:
                code = get_code(
                    gemaal.ide_gb1,
                    gemaal.ide_kn1,
                    gemaal.ide_gb2,
                    gemaal.ide_kn2,
                    str(i),
                )

                pumpstation = {
                    "code": code,
                    "display_name": code,
                    "start_node.code": get_code(gemaal.ide_gb1, gemaal.ide_kn1),
                    "end_node.code": get_code(gemaal.ide_gb2, gemaal.ide_kn2),
                    "start_level": getattr(gemaal, "pmp_an%i" % i, None),
                    "lower_stop_level": getattr(gemaal, "pmp_af%i" % i, None),
                    "upper_stop_level": getattr(gemaal, "rel_af%i" % i, None),
                    "capacity": getattr(gemaal, "pmp_pc%i" % i, None),
                    "sewerage": True,
                }

                self.output["pumpstations"].append(pumpstation)

    def parse_doorlaat(self, doorlaat):
        code = get_code(
            doorlaat.ide_gb1,
            doorlaat.ide_kn1,
            doorlaat.ide_gb2,
            doorlaat.ide_kn2,
            doorlaat.num_mvb,
        )

        orifice = {
            "code": code,
            "display_name": code,
            "start_node.code": get_code(doorlaat.ide_gb1, doorlaat.ide_kn1),
            "end_node.code": get_code(doorlaat.ide_gb2, doorlaat.ide_kn2),
            "cross_section_details": {
                "shape": self.get_shape(doorlaat.pro_vrm, code),
                "width": get_value(doorlaat.pro_bre, float),
                "height": get_value(doorlaat.pro_hgt, float),
            },
            "discharge_coefficient_positive": doorlaat.drl_coe,
            "discharge_coefficient_negative": doorlaat.drl_coe,
            "sewerage": True,
            "max_capacity": doorlaat.drl_cap,
            "crest_type": Constants.CREST_TYPE_SHARP_CRESTED,
            "crest_level": doorlaat.pro_bok,
        }

        try:
            str_rch = int(doorlaat.str_rch)
        except ValueError:
            logger.exception(
                "doorlaat.str_rch si not an integer: '%s', using 0", doorlaat.str_rch
            )
            str_rch = 0

        if str_rch in (1, 3):
            orifice["discharge_coefficient_negative"] = 0.0
        if str_rch in (2, 3):
            orifice["discharge_coefficient_positive"] = 0.0

        self.output["orifices"].append(orifice)

        return check_unsupported_fields(orifice, "qdh_num", "qdh_niv")

    def parse_overstort(self, overstort):

        code = get_code(
            overstort.ide_gb1,
            overstort.ide_kn1,
            overstort.ide_gb2,
            overstort.ide_kn2,
            overstort.num_mvb,
        )

        value = getattr(
            overstort,
            "bws_gem",
            getattr(overstort, "bws_zom", getattr(overstort, "bws_win", None)),
        )

        if value is not None:
            timeseries = "0,{0}\n9999,{0} ".format(value)
        else:
            timeseries = None

        weir = {
            "code": code,
            "display_name": code,
            "start_node.code": get_code(overstort.ide_gb1, overstort.ide_kn1),
            "end_node.code": get_code(overstort.ide_gb2, overstort.ide_kn2),
            "cross_section_details": {
                "shape": Constants.SHAPE_RECTANGLE,
                "width": overstort.ovs_bre,
                "height": None,
            },
            "crest_type": Constants.CREST_TYPE_SHARP_CRESTED,
            "crest_level": overstort.ovs_niv,
            "discharge_coefficient_positive": overstort.ovs_coe,
            "discharge_coefficient_negative": overstort.ovs_coe,
            "sewerage": True,
            "boundary_details": {
                "timeseries": timeseries,
                "boundary_type": Constants.BOUNDARY_TYPE_WATERLEVEL,
            },
        }

        try:
            str_rch = int(overstort.str_rch)
        except ValueError:
            logger.exception(
                "overstort.str_rch is not an int: '%s', using 0", overstort.str_rch
            )
            str_rch = 0

        if str_rch in (1, 3):
            weir["discharge_coefficient_negative"] = 0.0
        if str_rch in (2, 3):
            weir["discharge_coefficient_positive"] = 0.0

        self.output["weirs"].append(weir)

        return check_unsupported_fields(weir, "qdh_num", "qdh_niv")

    def parse_uitlaat(self, uitlaat):

        code = get_code(uitlaat.ide_gb1, uitlaat.ide_kn1)

        value = getattr(
            uitlaat,
            "bws_gem",
            getattr(uitlaat, "bws_zom", getattr(uitlaat, "bws_win", None)),
        )

        outlet = {
            "node.code": code,
            "boundary_type": Constants.BOUNDARY_TYPE_WATERLEVEL,
            "timeseries": None,
        }

        if value is not None:
            outlet["timeseries"] = "0,{0}\n9999,{0} ".format(value)

        self.output["outlets"].append(outlet)

        return check_unsupported_fields(outlet, "ide_gb2", "ide_kn2")

    def parse_bergend_oppervlak(self, berging):

        code = get_code(berging.ide_geb, berging.ide_knp)

        storage = {
            "node.code": code,
            "bottom_level": berging.niv_001,
            "storage_area": berging.bop_001,
        }
        self.output["storage"].append(storage)

        return check_unsupported_fields(
            storage, "niv_002", "bop_002", "niv_003", "bop_003", "niv_004", "bop_004"
        )

    def parse_koppeling(self, koppeling):

        code = get_code(
            koppeling.ide_gb1,
            koppeling.ide_kn1,
            koppeling.ide_gb2,
            koppeling.ide_kn2,
            koppeling.num_mvb,
        )

        if koppeling.typ_gkn != "01":
            # only combine of first is real. Definition is not clear,
            # but assumed is that '00' is real (also the default) and
            # '01' is fictive
            link = {
                "code": code,
                "start_node.code": get_code(koppeling.ide_gb1, koppeling.ide_kn1),
                "end_node.code": get_code(koppeling.ide_gb2, koppeling.ide_kn2),
            }
            self.output["links"].append(link)

        return []

    def parse_afvoerend_oppervlak(self, afvopp):

        connection_nodes = [get_code(afvopp.ide_gb1, afvopp.ide_kn1)]

        if afvopp.ide_kn2 != "":
            # special treatment required for some files from kikker
            if afvopp.ide_gb2 == "":
                afvopp.ide_gb2 = afvopp.ide_gb1

            connection_nodes.append(get_code(afvopp.ide_gb2, afvopp.ide_kn2))

        base_code = "-".join(connection_nodes)

        if afvopp.num_mvb is not None and afvopp.num_mvb != "":
            base_code += "-" + str(afvopp.num_mvb)

        for class_type in ["gvh", "ovh", "dak", "onv"]:

            unit = getattr(afvopp, "{0}_een".format(class_type))

            if unit == "01":
                logger.error("Unit type 01 for *AFV is not supported")

            for inclination_type in ["hel", "vla", "vlu"]:

                drainage_area_type = "{0}_{1}".format(class_type, inclination_type)

                if (
                    getattr(afvopp, drainage_area_type) is not None
                    and getattr(afvopp, drainage_area_type) > 0.001
                ):

                    code = "{0}-{1}".format(base_code, drainage_area_type)

                    drainage_area = {
                        "code": code,
                        "surface_class": self.get_surface_class(class_type),
                        "surface_inclination": self.get_surface_inclination(
                            inclination_type
                        ),
                        "area": getattr(afvopp, drainage_area_type),
                    }
                    self.output["impervious_surfaces"].append(drainage_area)

                    percentage = 100.0 / len(connection_nodes)

                    for node in connection_nodes:
                        imp_map = {
                            "node.code": node,
                            "imp_surface.code": code,
                            "percentage": percentage,
                        }
                        self.output["impervious_surface_maps"].append(imp_map)
