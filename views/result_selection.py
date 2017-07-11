# -*- coding: utf-8 -*-
import json
import os
import tempfile
import urllib2

from lizard_connector.connector import Endpoint
from PyQt4.QtNetwork import (
    QNetworkAccessManager, QNetworkRequest
)
from PyQt4.QtCore import pyqtSignal, QSettings, QModelIndex, QUrl, QFile
from PyQt4.QtGui import QWidget, QFileDialog, QMessageBox
from PyQt4.QtSql import QSqlDatabase
from PyQt4 import uic
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QGis

from ..datasource.netcdf import (find_id_mapping_file, layer_qh_type_mapping)
from ..utils.user_messages import pop_up_info
from .log_in_dialog import LoginDialog


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), os.pardir, 'ui',
    'threedi_result_selection_dialog.ui'))


class ThreeDiResultSelectionWidget(QWidget, FORM_CLASS):
    """Dialog for selecting model (spatialite and result files netCDFs)"""
    closingDialog = pyqtSignal()

    def __init__(
            self, parent=None, iface=None, ts_datasource=None,
            download_result_model=None, parent_class=None):
        """Constructor

        :parent: Qt parent Widget
        :iface: QGiS interface
        :ts_datasource: TimeseriesDatasourceModel instance
        :download_result_model: DownloadResultModel instance
        :parent_class: the tool class which instantiated this widget. Is used
             here for storing volatile information
        """
        super(ThreeDiResultSelectionWidget, self).__init__(parent)

        self.parent_class = parent_class
        self.iface = iface
        self.setupUi(self)

        # login administration
        self.login_dialog = LoginDialog()
        self.login_dialog.log_in_button.clicked.connect(self.handle_log_in)

        # download administration
        self.network_manager = QNetworkAccessManager(self)

        # set models on table views and update view columns
        self.ts_datasource = ts_datasource
        self.resultTableView.setModel(self.ts_datasource)
        self.ts_datasource.set_column_sizes_on_view(self.resultTableView)
        self.download_result_model = download_result_model
        self.downloadResultTableView.setModel(self.download_result_model)
        self.download_result_model.set_column_sizes_on_view(
            self.downloadResultTableView)

        if self.download_result_model.rowCount() > 0:
            self.downloadResultTableView.setEnabled(True)
            self.downloadResultButton.setEnabled(True)

        # connect signals
        self.selectTsDatasourceButton.clicked.connect(
            self.select_ts_datasource)
        self.closeButton.clicked.connect(self.close)
        self.removeTsDatasourceButton.clicked.connect(
            self.remove_selected_ts_ds)
        self.selectModelSpatialiteButton.clicked.connect(
            self.select_model_spatialite_file)
        # connect signals for the downloader
        self.loginButton.clicked.connect(self.on_login_button_clicked)
        # self.downloadResultButton.clicked.connect(self.handle_download)

        # set combobox list
        combo_list = [ds for ds in self.get_3di_spatialites_legendlist()]

        if self.ts_datasource.model_spatialite_filepath and \
                self.ts_datasource.model_spatialite_filepath not in combo_list:
            combo_list.append(self.ts_datasource.model_spatialite_filepath)

        if not self.ts_datasource.model_spatialite_filepath:
            combo_list.append('')

        self.modelSpatialiteComboBox.addItems(combo_list)

        if self.ts_datasource.model_spatialite_filepath:
            current_index = self.modelSpatialiteComboBox.findText(
                self.ts_datasource.model_spatialite_filepath)

            self.modelSpatialiteComboBox.setCurrentIndex(
                current_index)
        else:
            current_index = self.modelSpatialiteComboBox.findText('')
            self.modelSpatialiteComboBox.setCurrentIndex(current_index)

        self.modelSpatialiteComboBox.currentIndexChanged.connect(
            self.model_spatialite_change)

    def on_close(self):
        """
        Clean object on close
        """
        self.selectTsDatasourceButton.clicked.disconnect(
            self.select_ts_datasource)
        self.closeButton.clicked.disconnect(self.close)
        self.removeTsDatasourceButton.clicked.disconnect(
            self.remove_selected_ts_ds)
        self.selectModelSpatialiteButton.clicked.connect(
            self.select_model_spatialite_file)

    def closeEvent(self, event):
        """
        Close widget, called by Qt on close
        :param event: QEvent, close event
        """
        self.closingDialog.emit()
        self.on_close()
        event.accept()

    def select_ts_datasource(self):
        """
        Open File dialog for selecting netCDF result files, triggered by button
        :return: boolean, if file is selected
        """

        settings = QSettings('3di', 'qgisplugin')

        try:
            init_path = settings.value('last_used_datasource_path', type=str)
        except TypeError:
            init_path = os.path.expanduser("~")

        filename = QFileDialog.getOpenFileName(self,
                                               'Open resultaten file',
                                               init_path,
                                               'NetCDF (*.nc)')

        if filename:
            # Little test for checking if there is an id mapping file available
            # If not we're not going to proceed.
            try:
                find_id_mapping_file(filename)
            except IndexError:
                pop_up_info("No id mapping file found, we tried the following "
                            "locations: [., ../input_generated]. Please add "
                            "this file to the correct location and try again.",
                            title='Error')
                return False

            # Add to the datasource
            items = [{
                'type': 'netcdf',
                'name': os.path.basename(filename).lower().rstrip('.nc'),
                'file_path': filename
            }]
            self.ts_datasource.insertRows(items)
            settings.setValue('last_used_datasource_path',
                              os.path.dirname(filename))

            return True

        return False

    def remove_selected_ts_ds(self):
        """
        Remove selected result files from model, called by 'remove' button
        """

        selection_model = self.resultTableView.selectionModel()
        # get unique rows in selected fields
        rows = set([index.row()
                    for index in selection_model.selectedIndexes()])
        for row in reversed(sorted(rows)):
            self.ts_datasource.removeRows(row, 1)

    def get_3di_spatialites_legendlist(self):
        """
        Get list of spatialite data sources currently active in canvas
        :return: list of strings, unique spatialite paths
        """

        tdi_spatialites = []

        for layer in self.iface.legendInterface().layers():
            if layer.name() in layer_qh_type_mapping.keys() and \
                    layer.dataProvider().name() == 'spatialite':
                source = layer.dataProvider().dataSourceUri().split("'")[1]
                if source not in tdi_spatialites:
                    tdi_spatialites.append(source)

        return tdi_spatialites

    def model_spatialite_change(self, nr):
        """
        Change active modelsource. Called by combobox when selected
        spatialite changed
        :param nr: integer, nr of item selected in combobox
        """

        self.ts_datasource.model_spatialite_filepath = \
            self.modelSpatialiteComboBox.currentText()
        # Just emitting some dummy model indices cuz what else can we do, there
        # is no corresponding rows/columns that's been changed
        self.ts_datasource.dataChanged.emit(QModelIndex(), QModelIndex())

    def select_model_spatialite_file(self):
        """
        Open file dialog on click on button 'load model'
        :return: Boolean, if file is selected
        """

        settings = QSettings('3di', 'qgisplugin')

        try:
            init_path = settings.value('last_used_spatialite_path', type=str)
        except TypeError:
            init_path = os.path.expanduser("~")

        filename = QFileDialog.getOpenFileName(
            self,
            'Open 3Di model spatialite file',
            init_path,
            'Spatialite (*.sqlite)')

        if filename == "":
            return False

        self.ts_datasource.spatialite_filepath = filename
        index_nr = self.modelSpatialiteComboBox.findText(filename)

        if index_nr < 0:
            self.modelSpatialiteComboBox.addItem(filename)
            index_nr = self.modelSpatialiteComboBox.findText(filename)

        self.modelSpatialiteComboBox.setCurrentIndex(index_nr)

        settings.setValue('last_used_spatialite_path',
                          os.path.dirname(filename))
        return True

    def on_login_button_clicked(self):
        self.login_dialog.show()

    def handle_log_in(self):
        """Function to handle logging in and populating DownloadResultModel.
        """
        # Get the username and password
        username = self.login_dialog.user_name_input.text()
        password = self.login_dialog.user_password_input.text()

        if not username or not password:
            pop_up_info("Username or password cannot be empty.")
            return

        scenarios_endpoint = Endpoint(
            username=username,
            password=password,
            endpoint='scenarios',
            all_pages=False,
        )
        try:
            results = scenarios_endpoint.download(page_size=10)
        except urllib2.HTTPError as e:
            if e.code == 401:
                pop_up_info("Incorrect username and/or password.")
            else:
                pop_up_info(str(e))
        else:
            items = [
                {
                    'name': r['name'],
                    'url': r['url'],
                    'size_bytes': r['total_size'],
                    'results': r['result_set'],
                }
                for r in results
            ]
            self.username = username
            self.password = password
            self.download_result_model.insertRows(items)
            # TODO: some duplicate code below. Use signals on model maybe?
            self.downloadResultTableView.setEnabled(True)
            self.downloadResultButton.setEnabled(True)

            self.login_dialog.close()

    @property
    def username(self):
        return self.parent_class.username

    @username.setter
    def username(self, username):
        self.parent_class.username = username

    @property
    def password(self):
        return self.parent_class.password

    @password.setter
    def password(self, password):
        self.parent_class.password = password
