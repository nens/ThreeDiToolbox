from qgis.core import QgsProject
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

import logging
import os


logger = logging.getLogger(__name__)

FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), os.pardir, "ui", "tool_dialog.ui")
)


class ToolDialogWidget(QDialog, FORM_CLASS):
    def __init__(self, parent=None, iface=None, ts_datasource=None, command=None):
        """Constructor

        Args:
            parent: Qt parent Widget
            iface: QGiS interface
            ts_datasource: TimeseriesDatasourceModel instance
            command: Command instance with a run_it method which will be called
                     on acceptance of the dialog
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iface = iface
        self.ts_datasource = ts_datasource
        self.command = command

        # Populate combo boxes
        self.layers = QgsProject.instance().layerTreeRoot().findLayers()

        # Note: the order in the combo box is the same as in the QGIS layer
        # selection box, so there should be no ambiguity even if layers have
        # the same name because you know the order.
        layer_names = [l.name() for l in self.layers]
        self.layerComboBox.addItems(layer_names)
        # Populate datasource combo box
        self.datasources = self.ts_datasource.rows
        self.datasource_names = [d.file_path.value for d in self.datasources]
        self.datasourceComboBox.addItems(self.datasource_names)

        # These variables are selected by the combo box. Because the combobox
        # 'activated' signal only fires when you click on it and doesn't set
        # the items the first time you open the dialog, we've got to
        # explicitly set the the first item as being implicitly selected
        # already because that's what most users would expect.
        if self.layers:
            self.selected_layer = self.layers[0].layer()
        else:
            self.selected_layer = None
        if self.ts_datasource.rows:
            self.selected_datasource = self.ts_datasource.rows[0]
        else:
            self.selected_datasource = None

        # Connect signals
        self.layerComboBox.activated[int].connect(self.on_layerbox_activate)
        self.datasourceComboBox.activated[int].connect(self.on_datasourcebox_activate)
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

    def on_layerbox_activate(self, idx):
        self.selected_layer = self.layers[idx].layer()
        logger.debug("Selected layer: %s", self.selected_layer.name())

    def on_datasourcebox_activate(self, idx):
        self.selected_datasource = self.datasources[idx]
        logger.debug(
            "Selected datasource: %s", self.selected_datasource.file_path.value
        )

    def on_accept(self):
        """Accept and run the Command.run_it method."""
        self.accept()
        self.command.run_it(
            layer=self.selected_layer, datasource=self.selected_datasource
        )

    def on_reject(self):
        """Cancel"""
        self.reject()

    def closeEvent(self, event):
        """
        Close widget, called by Qt on close
        :param event: QEvent, close event
        """
        # Clean up signals
        self.buttonBox.accepted.disconnect(self.on_accept)
        self.buttonBox.rejected.disconnect(self.on_reject)
        self.layerComboBox.activated[int].disconnect(self.on_layerbox_activate)
        self.datasourceComboBox.activated[int].disconnect(
            self.on_datasourcebox_activate
        )
        event.accept()
