from pathlib import Path
from sqlalchemy import update
from threedi_results_analysis.processing.deps.sql_models.constants import Constants
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import BoundaryCondition1D
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import ConnectionNode
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Manhole
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Pipe
from threedi_results_analysis.processing.deps.sql_models.model_schematisation import Pumpstation
from threedi_results_analysis.tests.test_init import TEST_DATA_DIR
from threedi_results_analysis.processing.deps.guess_indicator import guess_indicators_utils
from threedi_results_analysis.utils.threedi_database import ThreediDatabase

import pytest
import shutil


def get_pump_or_outlet_manholes(session, ids):
    """Get either manhole_outlet OR manhole_pump from sqlite.
    :param ids: [list] this contains ids from either manhole_outlet or manhole_pump
    :return: a dict with key=manhole.id, value=manhole.manhole_indicator
    """
    manholes_id_indicator = {}
    # only return manhole
    sql_manholes = (
        session.query(Manhole)
        .join(Manhole.connection_node)
        .filter(ConnectionNode.id.in_(ids))
    )
    for manhole in sql_manholes:
        # fill dict
        manholes_id_indicator[manhole.id] = manhole.manhole_indicator
    return manholes_id_indicator


def get_all_manholes(session):
    """Get all manholes from sqlite (also manhole_outlet, manhole_pump).
    :return: a dict with key=manhole.id, value=manhole.manhole_indicator"""
    manholes_id_indicator = {}
    sql_manholes = session.query(Manhole)
    for manhole in sql_manholes:
        # fill dict
        manholes_id_indicator[manhole.id] = manhole.manhole_indicator
    return manholes_id_indicator


def get_manholes(session, get_only_outlets=False, get_only_pumps=False, get_all=False):
    """Get manholes from sqlite: OR only manhole_outlet, OR only manhole_pumps, OR
    all manholes (manhole_outlet + manhole_pump + other manholes).
    :return: manholes_id_indicator = a dict with key=id, value=manhole_indicator
    :param session: sqlalchemy.orm.session
    :param get_only_outlets: (boolean) only get manholes that are located on an outlet.
    This means that a 1D boundary condition is located on the manhole.
    :param get_only_pumps: (boolean) only get manholes that are located on an startnode
    of a pumpstation.
    :param get_all: manhole on outlet + manhole on pumpstation + other manholes
    :return: manholes_id_indicator: (dict)
    """
    # only 1 of kwargs may be True
    assert sum([get_only_outlets, get_only_pumps, get_all]) == 1
    if get_only_pumps:
        ids = session.query(Pumpstation.connection_node_start_id)
    elif get_only_outlets:
        ids = session.query(BoundaryCondition1D.connection_node_id)
    if get_only_pumps or get_only_outlets:
        manholes_id_indicator = get_pump_or_outlet_manholes(session, ids)
    if get_all:
        manholes_id_indicator = get_all_manholes(session)
    return manholes_id_indicator


def get_all_pipes(session):
    pipes = {}
    # only return manhole
    sql_pipes = session.query(Pipe)
    for pipe in sql_pipes:
        # fill dict
        pipes[pipe.id] = (pipe.friction_type, pipe.friction_value, pipe.material)
    return pipes


def empty_manhole_indicator(session, manholes_pre_empty):
    """Empty column manhole_indicator (set is to NULL) of table v2_manhole."""
    manholes_ids = list(manholes_pre_empty)
    update_query = (
        update(Manhole)
        .where(Manhole.id.in_(manholes_ids))
        .values(manhole_indicator=None)
    )
    session.execute(update_query)
    session.commit()


def empty_pipe_friction_value(session, pipes_pre_empty):
    """empty column manhole_indicator (set is to NULL) of table v2_manhole"""
    pipes_ids = list(pipes_pre_empty)
    update_query = (
        update(Pipe)
        .where(Pipe.id.in_(pipes_ids))
        .values(friction_value=None, friction_type=None)
    )
    session.execute(update_query)
    session.commit()


@pytest.fixture()
def db(tmpdir):
    """Copy original sqlite to tmpdir as we modify the sqlite data (with sqlalchemy
    in these tests. Pytest fixes cleanup op tmpdir: "entries older than 3 temporary
    directories will be removed"."""
    sqlite_filename = "v2_bergermeer.sqlite"
    orig_sqlite_path = TEST_DATA_DIR / "testmodel" / "v2_bergermeer" / sqlite_filename
    tmp_sqlite_dir = Path(tmpdir)
    tmp_sqlite_path = tmp_sqlite_dir / sqlite_filename
    shutil.copy2(orig_sqlite_path, tmp_sqlite_path)
    db_type = "spatialite"
    db_set = {"db_path": tmp_sqlite_path}
    db = ThreediDatabase(db_set, db_type)
    return db


def test_guess_manhole_indicator(db):
    session = db.get_session()

    # before we empty manholes, first get their [(id, manhole_indicator)]
    manholes_pumps_pre_empty = get_manholes(session, get_only_pumps=True)
    manholes_outlets_pre_empty = get_manholes(session, get_only_outlets=True)
    all_manholes_pre_empty = get_manholes(session, get_all=True)
    assert all_manholes_pre_empty, (
        "sqlite should have manholes, otherwise there is " "nothing to test"
    )

    # now lets empty column 'manhole_indicator' in all manholes
    empty_manhole_indicator(session, all_manholes_pre_empty)

    all_manholes_pre_guess = get_manholes(session, get_all=True)
    # all dict values should be None (<-- still test-prework, not actual testing), If
    # it fails then empty_manhole_selection() does not a good job
    assert not all(list(all_manholes_pre_guess.values()))

    # now put guesser to work
    guesser = guess_indicators_utils.Guesser(db)
    guesser.guess_manhole_indicator(only_empty_fields=False)

    # get a new session
    session = db.get_session()

    manholes_pumps_after_guess = get_manholes(session, get_only_pumps=True)
    manholes_outlet_after_guess = get_manholes(session, get_only_outlets=True)
    all_manholes_after_guess = get_manholes(session, get_all=True)

    # manholes_pumps should have been updated to MANHOLE_INDICATOR_PUMPSTATION
    if manholes_pumps_pre_empty:
        manholes_pumps = list(manholes_pumps_after_guess.values())
        expected_value = Constants.MANHOLE_INDICATOR_PUMPSTATION
        assert all([expected_value == manhole for manhole in manholes_pumps])

    # manholes_outlets should have been updated to MANHOLE_INDICATOR_OUTLET
    if manholes_outlets_pre_empty:
        manholes_outlets = list(manholes_outlet_after_guess.values())
        expected_value = Constants.MANHOLE_INDICATOR_OUTLET
        assert all([expected_value == manhole for manhole in manholes_outlets])

        for k in manholes_outlets_pre_empty:
            all_manholes_after_guess.pop(k, None)

    # The rest of the manholes should have been updated to MANHOLE_INDICATOR_MANHOLE
    # To check this, we first pop the manholes_pumps and manholes_outlets from
    # all_manholes
    for manhole_dict in [manholes_pumps_pre_empty, manholes_outlets_pre_empty]:
        for manhole_id in manhole_dict:
            all_manholes_after_guess.pop(manhole_id, None)

    all_manholes = list(all_manholes_after_guess.values())
    expected_value = Constants.MANHOLE_INDICATOR_MANHOLE
    assert all([expected_value == manhole for manhole in all_manholes])


def test_guess_pipe_friction(db):
    session = db.get_session()
    pipes_pre_empty = get_all_pipes(session)
    assert pipes_pre_empty, (
        "sqlite should have pipes, otherwise there is nothing to " "test"
    )

    # now lets empty columns 'friction_type' and 'friction_value' in all pipes
    empty_pipe_friction_value(session, pipes_pre_empty)

    pipes_after_emtpy = get_all_pipes(session)
    friction_types = [x[0] for x in list(pipes_after_emtpy.values())]
    friction_values = [x[1] for x in list(pipes_after_emtpy.values())]
    # all friction_types and friction_values should be None (<-- still test-prework,
    # not actual testing), If it fails then empty_pipe_friction_value() doesnt work
    assert not all(friction_types)
    assert not all(friction_values)

    # now put guesser to work
    guesser = guess_indicators_utils.Guesser(db)
    guesser.guess_pipe_friction(only_empty_fields=False)

    # get a new session
    session = db.get_session()
    pipes_after_guess = get_all_pipes(session)

    # all friction_types must have been updated to FRICTION_TYPE_MANNING
    assert all(
        [
            x[0] == Constants.FRICTION_TYPE_MANNING
            for x in list(pipes_after_guess.values())
        ]
    )

    material_frictionvalue_mapping = {}
    # Constants.TABLE_MANNING is a set with tup
    for material, friction_value in Constants.TABLE_MANNING:
        material_frictionvalue_mapping[material] = friction_value

    # all friction_values 'x[1]' must have been updated to correct friction_value
    # this friction_values depends on material 'x[2]'
    assert all(
        [
            x[1] == material_frictionvalue_mapping[x[2]]
            for x in list(pipes_after_guess.values())
        ]
    )
