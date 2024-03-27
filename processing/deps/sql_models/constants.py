def reversed_dict(d):
    """Create a reverse lookup dictionary"""
    return dict([(b, a) for a, b in d])


class Constants(object):
    """Constants for all databases, or unsorted"""

    CALCULATION_TYPE_EMBEDDED = 0
    CALCULATION_TYPE_ISOLATED = 1
    CALCULATION_TYPE_CONNECTED = 2
    CALCULATION_TYPE_DOUBLE_CONNECTED = 5

    CALCULATION_TYPE_CHOICES = (
        (CALCULATION_TYPE_EMBEDDED, "embedded"),
        (CALCULATION_TYPE_ISOLATED, "isolated"),
        (CALCULATION_TYPE_CONNECTED, "connected"),
        (CALCULATION_TYPE_DOUBLE_CONNECTED, "double connected"),
    )
    CALCULATION_TYPES = dict(CALCULATION_TYPE_CHOICES)

    # FRICTION TYPES
    FRICTION_TYPE_CHEZY = 1
    FRICTION_TYPE_MANNING = 2
    # FRICTION_TYPE_NIKURADSE = 999 # not supported

    FRICTION_TYPE_CHOICES = (
        (FRICTION_TYPE_CHEZY, "chezy [m^(1/2)/s]"),
        (FRICTION_TYPE_MANNING, "manning nm [s/m^(1/2)]"),
        # (FRICTION_TYPE_NIKURADSE, 'nikuradse (White-Coolbrook) [mm]'),
    )
    FRICTION_TYPES = dict(FRICTION_TYPE_CHOICES)

    # SHAPES FOR MANHOLES
    MANHOLE_SHAPE_SQUARE = "sqr"
    MANHOLE_SHAPE_RECTANGLE = "rect"
    MANHOLE_SHAPE_ROUND = "rnd"

    # SHAPES FOR PIPES
    SHAPE_RECTANGLE = 1
    SHAPE_ROUND = 2
    SHAPE_EGG = 3
    # SHAPE_YZ = 4 -- not in use
    SHAPE_TABULATED_RECTANGLE = 5
    SHAPE_TABULATED_TRAPEZIUM = 6

    PROFILE_SHAPE_CHOICES = (
        (SHAPE_RECTANGLE, "rectangle"),
        (SHAPE_ROUND, "round"),
        (SHAPE_EGG, "egg"),
        # (SHAPE_YZ, 'yz'),
        (SHAPE_TABULATED_RECTANGLE, "tabulated rectangle"),
        (SHAPE_TABULATED_TRAPEZIUM, "tabulated trapezium"),
    )

    PROFILE_SHAPES = dict(PROFILE_SHAPE_CHOICES)
    PROFILE_SHAPES_LOOKUP = reversed_dict(PROFILE_SHAPE_CHOICES)

    MANHOLE_SHAPE_CHOICES = (
        (MANHOLE_SHAPE_ROUND, "round"),
        (MANHOLE_SHAPE_SQUARE, "square"),
        (MANHOLE_SHAPE_RECTANGLE, "rectangle"),
    )

    MANHOLE_SHAPES = dict(MANHOLE_SHAPE_CHOICES)
    MANHOLE_SHAPES_LOOKUP = reversed_dict(MANHOLE_SHAPE_CHOICES)

    # MATERIALS
    MATERIAL_TYPE_CONCRETE = 0
    MATERIAL_TYPE_PVC = 1
    MATERIAL_TYPE_STONEWARE = 2
    MATERIAL_TYPE_CAST_IRON = 3
    MATERIAL_TYPE_BRICKWORK = 4
    MATERIAL_TYPE_HPE = 5
    MATERIAL_TYPE_HPDE = 6
    MATERIAL_TYPE_SHEET_IRON = 7
    MATERIAL_TYPE_STEEL = 8

    TABLE_MANNING = {
        (MATERIAL_TYPE_CONCRETE, 0.0145),
        (MATERIAL_TYPE_PVC, 0.0110),
        (MATERIAL_TYPE_STONEWARE, 0.0115),
        (MATERIAL_TYPE_CAST_IRON, 0.0135),
        (MATERIAL_TYPE_BRICKWORK, 0.0160),
        (MATERIAL_TYPE_HPE, 0.0110),
        (MATERIAL_TYPE_HPDE, 0.0110),
        (MATERIAL_TYPE_SHEET_IRON, 0.0135),
        (MATERIAL_TYPE_STEEL, 0.0130),
    }

    MATERIAL_TYPE_CHOICES = (
        (MATERIAL_TYPE_CONCRETE, "concrete"),
        (MATERIAL_TYPE_PVC, "pvc"),
        (MATERIAL_TYPE_STONEWARE, "stoneware"),
        (MATERIAL_TYPE_CAST_IRON, "cast-iron"),
        (MATERIAL_TYPE_BRICKWORK, "brickwork"),
        (MATERIAL_TYPE_HPE, "hpe"),
        (MATERIAL_TYPE_HPDE, "hpde"),
        (MATERIAL_TYPE_SHEET_IRON, "sheet-iron"),
        (MATERIAL_TYPE_STEEL, "steel"),
    )
    MATERIALS = dict(MATERIAL_TYPE_CHOICES)
    MATERIAL_LOOKUP = reversed_dict(MATERIAL_TYPE_CHOICES)

    # MATERIAL OF LEVEES
    LEVEE_MATERIAL_SAND = 1
    LEVEE_MATERIAAL_CLAY = 2

    LEVEE_MATERIAL_CHOICES = (
        (LEVEE_MATERIAL_SAND, "sand"),
        (LEVEE_MATERIAAL_CLAY, "clay"),
    )
    LEVEE_MATERIALS = dict(LEVEE_MATERIAL_CHOICES)

    CREST_TYPE_BROAD_CRESTED = 3
    CREST_TYPE_SHARP_CRESTED = 4

    CREST_TYPE_CHOICES = (
        (CREST_TYPE_BROAD_CRESTED, "broad crested"),
        (CREST_TYPE_SHARP_CRESTED, "sharp crested"),
    )
    CREST_TYPES = dict(CREST_TYPE_CHOICES)

    # BOUNDARY CONDITIONS
    BOUNDARY_TYPE_WATERLEVEL = 1
    BOUNDARY_TYPE_VELOCITY = 2
    BOUNDARY_TYPE_DISCHARGE = 3

    BOUNDARY_TYPE_CHOICES = (
        (BOUNDARY_TYPE_WATERLEVEL, "waterlevel"),
        (BOUNDARY_TYPE_VELOCITY, "velocity"),
        (BOUNDARY_TYPE_DISCHARGE, "discharge"),
    )
    BOUNDARY_TYPES = dict(BOUNDARY_TYPE_CHOICES)

    # manhole
    MANHOLE_INDICATOR_MANHOLE = 0
    MANHOLE_INDICATOR_OUTLET = 1
    MANHOLE_INDICATOR_PUMPSTATION = 2

    MANHOLE_INDICATOR_CHOICES = (
        (MANHOLE_INDICATOR_MANHOLE, "manhole"),
        (MANHOLE_INDICATOR_OUTLET, "outlet"),
        (MANHOLE_INDICATOR_PUMPSTATION, "pumpstation"),
    )
    MANHOLE_INDICATORS = dict(MANHOLE_INDICATOR_CHOICES)
    MANHOLE_INDICATOR_LOOKUP = reversed_dict(MANHOLE_INDICATOR_CHOICES)

    # sewerage types
    SEWERAGE_TYPE_COMBINED = 0
    SEWERAGE_TYPE_STORMWATER = 1  # RWA
    SEWERAGE_TYPE_WASTEWATER = 2  # DWA
    SEWERAGE_TYPE_TRANSPORT = 3
    SEWERAGE_TYPE_OVERFLOW = 4  # overstort
    SEWERAGE_TYPE_SINKER = 5
    SEWERAGE_TYPE_STORAGE = 6
    SEWERAGE_TYPE_STORAGE_SETTLING_TANK = 7

    SEWERAGE_TYPE_CHOICES = (
        (SEWERAGE_TYPE_COMBINED, "combined"),
        (SEWERAGE_TYPE_STORMWATER, "stormwater"),  # RWA
        (SEWERAGE_TYPE_WASTEWATER, "wastewater"),  # DWA
        (SEWERAGE_TYPE_TRANSPORT, "transport"),
        (SEWERAGE_TYPE_OVERFLOW, "overflow"),
        (SEWERAGE_TYPE_SINKER, "sinker"),
        (SEWERAGE_TYPE_STORAGE, "storage"),
        (SEWERAGE_TYPE_STORAGE_SETTLING_TANK, "storage-settling-tank"),
    )

    SEWERAGE_TYPES = dict(SEWERAGE_TYPE_CHOICES)
    SEWERAGE_TYPE_MAP = reversed_dict(list(SEWERAGE_TYPES.items()))

    # Global settings
    # 0: Euler implicit; 1: Carlson implicit 2: Silecki explicit
    INTEGRATION_METHOD_EULER_IMPLICIT = 0
    INTEGRATION_METHOD_CARLSON_IMPLICIT = 1
    INTEGRATION_METHOD_SILECKI_EXPLICIT = 2

    INTEGRATION_METHOD_CHOICES = (
        (INTEGRATION_METHOD_EULER_IMPLICIT, "euler-implicit"),
        (INTEGRATION_METHOD_CARLSON_IMPLICIT, "carlson-implicit"),
        (INTEGRATION_METHOD_SILECKI_EXPLICIT, "silecki-explicit"),
    )
    INTEGRATION_METHODS = dict(INTEGRATION_METHOD_CHOICES)

    # SURFACE_CLASS SURFACE_INCLINATION RIONED
    # gesloten verharding hellend gvh_hel
    # gesloten verharding vlak gvh_vla
    # gesloten verharding uitgestrekt gvh_vlu
    # open verharding hellend ovh_hel
    # open verharding vlak ovh_vla
    # open verharding uitgestrekt ovh_vlu
    # onverhard hellend onv_hel
    # onverhard vlak onv_vla
    # onverhard uitgestrekt onv_vlu
    # half verhard hellend onv_hel
    # half verhard vlak onv_vla
    # half verhard uitgestrekt onv_vlu
    # pand hellend dak_hel
    # pand vlak dak_vla
    # pand uitgestrekt dak_vlu
    SURFACE_CLASS_GESLOTEN_VERHARDING = "gesloten verharding"
    SURFACE_CLASS_OPEN_VERHARDING = "open verharding"
    SURFACE_CLASS_ONVERHARD = "onverhard"
    SURFACE_CLASS_HALF_VERHARD = "half verhard"
    SURFACE_CLASS_PAND = "pand"

    SURFACE_CLASS_CHOICES = (
        (SURFACE_CLASS_GESLOTEN_VERHARDING, "gesloten verharding"),
        (SURFACE_CLASS_OPEN_VERHARDING, "open verharding"),
        (SURFACE_CLASS_ONVERHARD, "onverhard"),
        (SURFACE_CLASS_HALF_VERHARD, "half verhard"),
        (SURFACE_CLASS_PAND, "pand"),
    )
    SURFACE_CLASSES = dict(SURFACE_CLASS_CHOICES)

    SURFACE_INCLINATION_HELLEND = "hellend"
    SURFACE_INCLINATION_VLAK = "vlak"
    SURFACE_INCLINATION_UITGESTREKT = "uitgestrekt"

    SURFACE_INCLINATION_CHOICES = (
        (SURFACE_INCLINATION_HELLEND, "hellend"),
        (SURFACE_INCLINATION_VLAK, "vlak"),
        (SURFACE_INCLINATION_UITGESTREKT, "uitgestrekt"),
    )
    SURFACE_INCLINATIONS = dict(SURFACE_INCLINATION_CHOICES)
