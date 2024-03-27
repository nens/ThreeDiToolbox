from PyQt5.QtCore import Qt
from threedi_results_analysis.tool_graph.graph_model import LocationTimeseriesModel

import unittest


class TestLocationTimeseriesModelItem(unittest.TestCase):
    """Test LocationTimeseriesModelItem created by LocationTimeseriesModel"""

    test_values = {
        "active": False,
        "color": [10, 20, 30],
        "object_id": 40,
        "object_name": "test_name",
    }

    def setUp(self):
        """Runs before each test."""
        pass

    def test_init_with_defaults(self):
        """test default values after initialisation"""
        model = LocationTimeseriesModel()
        item = model._create_item()

        self.assertEqual(item.active.value, True)
        self.assertEqual(item.object_id.value, None)

    def test_init_with_values(self):
        """test values after initialisation"""
        model = LocationTimeseriesModel()
        item = model._create_item(**self.test_values)

        self.assertEqual(item.active.value, self.test_values["active"])
        self.assertEqual(item.color.value, self.test_values["color"])
        self.assertEqual(item.object_id.value, self.test_values["object_id"])
        self.assertEqual(item.object_name.value, self.test_values["object_name"])

    def test_set_values(self):
        """test setting properties"""
        model = LocationTimeseriesModel(
            initial_data=[{"object_id": 1, "object_name": "object_1", "active": True}]
        )
        item = model.rows[0]

        item.active.value = False
        item.color.value = [30, 40, 50]
        item.object_name.value = "changed_name"

        self.assertEqual(item.active.value, False)
        self.assertEqual(item.color.value, [30, 40, 50])
        self.assertEqual(item.object_name.value, "changed_name")

    def test_get_field_settings(self):
        """test setting properties"""
        model = LocationTimeseriesModel()
        item = model._create_item(**self.test_values)

        self.assertEqual(item.active.default_value, True)
        self.assertEqual(item.active.column_width, 20)
        # column name still unclear
        # self.assertEqual(item.active.column_name, "")

        # todo: test column, get_fields
        # todo: test plots, get_timetables

    def tearDown(self):
        """Runs after each test."""
        pass


class TestLocationTimeseriesModel(unittest.TestCase):
    """Test LocationTimeseriesModel functions"""

    ts_datasources = "bla"

    initial_data = [
        {"object_id": 1, "object_name": "object_1", "active": True},
        {"object_id": 2, "object_name": "object_2", "active": True},
        {"object_id": 3, "object_name": "object_3", "active": False},
        {"object_id": 4, "object_name": "object_4", "active": False},
    ]

    additional_data = [
        {"object_id": 5, "object_name": "object_5", "active": True},
        {"object_id": 6, "object_name": "object_6", "active": True},
        {"object_id": 7, "object_name": "object_7", "active": False},
        {"object_id": 8, "object_name": "object_8", "active": False},
    ]

    def setUp(self):
        """Runs before each test."""
        pass

    def test_init(self):
        """test default values after initialisation"""
        collection = LocationTimeseriesModel(ts_datasources=self.ts_datasources)

        self.assertEqual(collection.rowCount(), 0)
        self.assertEqual(collection.columnCount(), 9)

        headers = [collection.headerData(i) for i in range(0, collection.columnCount())]

        self.assertListEqual(
            headers,
            # display column names
            ["active", "pattern", "label", "grid", "result", "id", "type", "object_type", "hover"],
        )

    def test_init_with_initial_data(self):
        """test default values after initialisation"""
        collection = LocationTimeseriesModel(
            ts_datasources=self.ts_datasources, initial_data=self.initial_data
        )

        self.assertEqual(collection.rowCount(), 4)
        self.assertEqual(collection.columnCount(), 9)
        self.assertEqual(
            collection.data(collection.createIndex(0, 0, None), role=Qt.DisplayRole),
            None,
        )

        #  Color is displayed as emptry string
        self.assertEqual(
            collection.data(collection.createIndex(0, 1, None), role=Qt.DisplayRole),
            "",
        )

        # self.assertEqual(
        #     collection.data(collection.createIndex(0, 2, None), role=Qt.DisplayRole), 1
        # )

        self.assertEqual(
            collection.data(collection.createIndex(0, 6, None), role=Qt.DisplayRole),
            "object_1",
        )

    def test_insert_remove_rows(self):
        """test insertRows and removeRows function"""

        collection = LocationTimeseriesModel(
            ts_datasources=self.ts_datasources, initial_data=self.initial_data
        )

        collection.insertRows(self.additional_data)

        self.assertEqual(collection.rowCount(), 8)
        self.assertEqual(collection.columnCount(), 9)

        self.assertEqual(
            collection.data(collection.createIndex(7, 6, None), role=Qt.DisplayRole),
            "object_8",
        )

        collection.removeRows(2, 4)

        self.assertEqual(collection.rowCount(), 4)

        self.assertEqual(
            collection.data(collection.createIndex(1, 6, None), role=Qt.DisplayRole),
            "object_2",
        )

        self.assertEqual(
            collection.data(collection.createIndex(2, 6, None), role=Qt.DisplayRole),
            "object_7",
        )

    def test_set_get_data(self):
        """test insertRows and removeRows function"""

        collection = LocationTimeseriesModel(
            ts_datasources=self.ts_datasources, initial_data=self.initial_data
        )

        # first test checkField
        collection.setData(
            collection.createIndex(0, 0), Qt.Unchecked, Qt.CheckStateRole
        )

        self.assertEqual(collection.rows[0].active.value, False)
        self.assertEqual(
            collection.data(collection.createIndex(0, 0, None), role=Qt.CheckStateRole),
            Qt.Unchecked,
        )

        collection.setData(collection.createIndex(0, 0), Qt.Checked, Qt.CheckStateRole)

        self.assertEqual(collection.rows[0].active.value, True)
        self.assertEqual(
            collection.data(collection.createIndex(0, 0, None), role=Qt.CheckStateRole),
            Qt.Checked,
        )

        # test valueField
        collection.setData(collection.createIndex(0, 5), 8, Qt.DisplayRole)

        self.assertEqual(collection.rows[0].object_id.value, 8)
        self.assertEqual(
            collection.data(collection.createIndex(0, 5, None), role=Qt.DisplayRole), 8
        )

    def tearDown(self):
        """Runs after each test."""
        pass
