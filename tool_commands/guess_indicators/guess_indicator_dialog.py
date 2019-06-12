from qgis.core import QgsDataSourceUri
from qgis.gui import QgsCredentialDialog
from qgis.PyQt.QtCore import QMetaObject
from qgis.PyQt.QtCore import QRect
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtSql import QSqlDatabase
from qgis.PyQt.QtWidgets import QCheckBox
from qgis.PyQt.QtWidgets import QComboBox
from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.QtWidgets import QDialogButtonBox
from qgis.PyQt.QtWidgets import QGroupBox
from qgis.PyQt.QtWidgets import QSizePolicy
from qgis.PyQt.QtWidgets import QVBoxLayout
from ThreeDiToolbox.utils.threedi_database import get_databases

import logging


logger = logging.getLogger(__name__)


class GuessIndicatorDialogWidget(QDialog):
    def __init__(self, parent=None, checks=[], command=None):
        """Constructor

        Args:
            parent: Qt parent Widget
            iface: QGiS interface
            command: Command instance with a run_it method which will be called
                     on acceptance of the dialog
        """
        super().__init__(parent)
        self.checks = checks
        self.setupUi(checks)

        self.command = command

        self.databases = get_databases()
        self.database_combo.addItems(list(self.databases.keys()))

        # Connect signals
        self.buttonBox.accepted.connect(self.on_accept)
        self.buttonBox.rejected.connect(self.on_reject)

        self.filename = None

    def on_accept(self):
        """Accept and run the Command.run_it method."""

        db_key = self.database_combo.currentText()

        settings = self.databases[db_key]
        db_set = settings["db_settings"]

        if settings["db_type"] == "spatialite":
            pass
        else:  # postgres

            successful_connection = False

            uname = db_set["username"]
            passwd = db_set["password"]
            msg = "Log in"

            while not successful_connection:

                uri = QgsDataSourceUri()
                uri.setConnection(
                    db_set["host"],
                    db_set["port"],
                    db_set["database"],
                    db_set["username"],
                    db_set["password"],
                )

                # try to connect
                # create a PostgreSQL connection using QSqlDatabase
                db = QSqlDatabase.addDatabase("QPSQL")
                # check to see if it is valid

                db.setHostName(uri.host())
                db.setDatabaseName(uri.database())
                try:
                    # port can be an empty string, e.g. for spatialite db's
                    db.setPort(int(uri.port()))
                except ValueError:
                    # TODO: I've seen this uri.port() handling before in some
                    # other file, this can probably be refactored.
                    pass
                db.setUserName(uri.username())
                db.setPassword(uri.password())

                # open (create) the connection
                if db.open():
                    successful_connection = True
                    break
                else:
                    # todo - provide feedback what is wrong
                    pass

                connInfo = uri.connectionInfo()
                (success, uname, passwd) = QgsCredentialDialog.instance().get(
                    connInfo, uname, passwd, msg
                )

                if success:
                    db_set["username"] = uname
                    db_set["password"] = passwd
                else:
                    return

        checks = []

        if self.check_manhole_indicator.isChecked():
            checks.append("manhole_indicator")

        if self.check_pipe_friction.isChecked():
            checks.append("pipe_friction")

        if self.check_manhole_area.isChecked():
            checks.append("manhole_area")

        self.command.run_it(
            checks,
            self.check_only_empty_fields.isChecked(),
            db_set,
            settings["db_type"],
        )

        self.accept()

    def on_reject(self):
        """Cancel"""
        self.reject()
        logger.debug("Reject")

    def closeEvent(self, event):
        """
        Close widget, called by Qt on close
        :param event: QEvent, close event
        """

        self.buttonBox.accepted.disconnect(self.on_accept)
        self.buttonBox.rejected.disconnect(self.on_reject)

        event.accept()

    def setupUi(self, checks):
        self.resize(515, 450)
        self.verticalLayout = QVBoxLayout(self)

        self.groupBox_2 = QGroupBox(self)
        self.groupBox_2.setObjectName("groupBox_2")
        self.database_combo = QComboBox(self.groupBox_2)
        self.database_combo.setGeometry(QRect(10, 30, 481, 34))

        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.database_combo.sizePolicy().hasHeightForWidth()
        )
        self.database_combo.setSizePolicy(sizePolicy)
        self.database_combo.setObjectName("database_combo")
        self.verticalLayout.addWidget(self.groupBox_2)

        self.groupBox = QGroupBox(self)
        self.verticalLayoutBox = QVBoxLayout(self.groupBox)

        self.check_pipe_friction = QCheckBox(self.groupBox)
        self.check_pipe_friction.setChecked(True)
        self.verticalLayoutBox.addWidget(self.check_pipe_friction)

        self.check_manhole_indicator = QCheckBox(self.groupBox)
        self.check_manhole_indicator.setChecked(True)
        self.verticalLayoutBox.addWidget(self.check_manhole_indicator)

        self.check_manhole_area = QCheckBox(self.groupBox)
        self.check_manhole_area.setChecked(True)
        self.verticalLayoutBox.addWidget(self.check_manhole_area)

        self.verticalLayout.addWidget(self.groupBox)

        self.check_only_empty_fields = QCheckBox(self)
        self.check_only_empty_fields.setChecked(True)
        self.verticalLayout.addWidget(self.check_only_empty_fields)

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi()
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        QMetaObject.connectSlotsByName(self)

    def retranslateUi(self):
        self.setWindowTitle("Guess indicators")
        self.groupBox_2.setTitle("Model schematisation database")

        self.groupBox.setTitle("Guess")
        self.check_pipe_friction.setText("Pipe friction")
        self.check_manhole_indicator.setText("Manhole indicator")
        self.check_only_empty_fields.setText("Only fill NULL fields")
        self.check_manhole_area.setText("Manhole area (only fills NULL fields)")
