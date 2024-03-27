# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import csv
import os
import shutil

from hydxlib.scripts import run_import_export
from hydxlib.scripts import write_logging_to_file
from pathlib import Path
from sqlalchemy.exc import OperationalError, DatabaseError
from threedi_results_analysis.processing.deps.sufhyd.import_sufhyd_main import Importer
from threedi_results_analysis.processing.deps.guess_indicator import guess_indicators_utils

from threedi_schema import ThreediDatabase
from threedi_modelchecker import ThreediModelChecker
from threedi_schema import errors
from threedi_results_analysis.processing.download_hydx import download_hydx

from threedi_results_analysis.utils.utils import backup_sqlite
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (
    QgsProject,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterFolderDestination,
    QgsProcessingParameterString,
    QgsVectorLayer,
)


def get_threedi_database(filename, feedback):
    try:
        threedi_db = ThreediDatabase(filename)
        threedi_db.check_connection()
        return threedi_db
    except (OperationalError, DatabaseError):
        feedback.pushWarning("Invalid spatialite file")
        return None


class MigrateAlgorithm(QgsProcessingAlgorithm):
    """
    Migrate 3Di model schema to the current version
    """

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, self.tr("3Di Spatialite"), extension="sqlite"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        filename = self.parameterAsFile(parameters, self.INPUT, context)
        threedi_db = get_threedi_database(filename=filename, feedback=feedback)
        if not threedi_db:
            return {self.OUTPUT: None}
        schema = threedi_db.schema
        try:
            schema.validate_schema()
            schema.set_spatial_indexes()
        except errors.MigrationMissingError:
            backup_filepath = backup_sqlite(filename)
            schema.upgrade(backup=False, upgrade_spatialite_version=True)
            schema.set_spatial_indexes()
            shutil.rmtree(os.path.dirname(backup_filepath))
        except errors.UpgradeFailedError:
            feedback.pushWarning(
                "The spatialite database schema cannot be migrated to the current version. Please contact the service desk for assistance."
            )
            return {self.OUTPUT: None}
        success = True
        return {self.OUTPUT: success}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "migrate"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Migrate Spatialite")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Schematisation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return MigrateAlgorithm()


class CheckSchematisationAlgorithm(QgsProcessingAlgorithm):
    """
    Run the schematisation checker
    """

    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    ADD_TO_PROJECT = "ADD_TO_PROJECT"

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT, self.tr("3Di Spatialite"), extension="sqlite"
            )
        )

        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT, self.tr("Output"), fileFilter="csv"
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.ADD_TO_PROJECT, self.tr("Add result to project"), defaultValue=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        self.add_to_project = self.parameterAsBoolean(
            parameters, self.ADD_TO_PROJECT, context
        )
        self.output_file_path = None
        input_filename = self.parameterAsFile(parameters, self.INPUT, context)
        threedi_db = get_threedi_database(filename=input_filename, feedback=feedback)
        if not threedi_db:
            return {self.OUTPUT: None}
        try:
            model_checker = ThreediModelChecker(threedi_db)
        except errors.MigrationMissingError:
            feedback.pushWarning(
                "The selected 3Di model does not have the latest migration. Please "
                "migrate your model to the latest version."
            )
            return {self.OUTPUT: None}
        schema = threedi_db.schema
        schema.set_spatial_indexes()
        generated_output_file_path = self.parameterAsFileOutput(
            parameters, self.OUTPUT, context
        )
        self.output_file_path = f"{os.path.splitext(generated_output_file_path)[0]}.csv"
        session = model_checker.db.get_session()
        session.model_checker_context = model_checker.context
        total_checks = len(model_checker.config.checks)
        progress_per_check = 100.0 / total_checks
        checks_passed = 0
        try:
            with open(self.output_file_path, "w", newline="") as output_file:
                writer = csv.writer(output_file)
                writer.writerow(
                    [
                        "level",
                        "error_code",
                        "id",
                        "table",
                        "column",
                        "value",
                        "description",
                    ]
                )
                for i, check in enumerate(model_checker.checks(level="info")):
                    model_errors = check.get_invalid(session)
                    for error_row in model_errors:
                        writer.writerow(
                            [
                                check.level.name,
                                check.error_code,
                                error_row.id,
                                check.table.name,
                                check.column.name,
                                getattr(error_row, check.column.name),
                                check.description(),
                            ]
                        )
                    checks_passed += 1
                    feedback.setProgress(int(checks_passed * progress_per_check))
        except PermissionError:
            # PermissionError happens for example when a user has the file already open
            # with Excel on Windows, which locks the file.
            feedback.pushWarning(
                f"Not enough permissions to write the file '{self.output_file_path}'.\n\n"
                "The file may be used by another program. Please close all "
                "other programs using the file or select another output "
                "file."
            )
            return {self.OUTPUT: None}

        return {self.OUTPUT: self.output_file_path}

    def postProcessAlgorithm(self, context, feedback):
        if self.add_to_project:
            if self.output_file_path:
                result_layer = QgsVectorLayer(
                    self.output_file_path, "3Di schematisation errors"
                )
                QgsProject.instance().addMapLayer(result_layer)
        return {self.OUTPUT: self.output_file_path}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "check_schematisation"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Check Schematisation")

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Schematisation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return CheckSchematisationAlgorithm()


class ImportSufHydAlgorithm(QgsProcessingAlgorithm):
    """
    Import data from SufHyd to a 3Di Spatialite
    """

    INPUT_SUFHYD_FILE = "INPUT_SUFHYD_FILE"
    TARGET_SQLITE = "TARGET_SQLITE"

    def initAlgorithm(self, config):
        self.addParameter(
                QgsProcessingParameterFile(self.INPUT_SUFHYD_FILE, self.tr("Sufhyd file"), extension="hyd"))

        self.addParameter(
            QgsProcessingParameterFile(
                self.TARGET_SQLITE,
                "Target 3Di Sqlite",
                extension="sqlite"
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        sufhyd_file = self.parameterAsString(parameters, self.INPUT_SUFHYD_FILE, context)
        out_path = self.parameterAsFile(parameters, self.TARGET_SQLITE, context)
        threedi_db = get_threedi_database(filename=out_path, feedback=feedback)
        if not threedi_db:
            return {}
        try:
            schema = threedi_db.schema
            schema.validate_schema()

        except errors.MigrationMissingError:
            feedback.pushWarning(
                "The selected 3Di spatialite does not have the latest database schema version. Please migrate this "
                "spatialite and try again: Processing > Toolbox > 3Di > Schematisation > Migrate spatialite"
            )
            return {}

        importer = Importer(sufhyd_file, threedi_db)
        importer.run_import()

        return {}

    def name(self):
        return "import_sufhyd"

    def displayName(self):
        return self.tr("Import Sufhyd")

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return "Schematisation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ImportSufHydAlgorithm()


class GuessIndicatorAlgorithm(QgsProcessingAlgorithm):
    """
    Guess manhole indicator, pipe friction and manhole storage
    area.
    """

    TARGET_SQLITE = "TARGET_SQLITE"
    PIPE_FRICTION = "PIPE_FRICTION"
    MANHOLE_INDICATOR = "MANHOLE_INDICATOR"
    MANHOLE_AREA = "MANHOLE_AREA"
    ONLY_NULL_FIELDS = "ONLY_NULL_FIELDS"

    def initAlgorithm(self, config):

        self.addParameter(
            QgsProcessingParameterFile(
                self.TARGET_SQLITE,
                "Target 3Di Sqlite",
                extension="sqlite"
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.PIPE_FRICTION,
                description="Pipe friction",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.MANHOLE_INDICATOR,
                description="Manhole indicator",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.MANHOLE_AREA,
                description="Manhole area (only fills NULL fields)",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.ONLY_NULL_FIELDS,
                description="Only fill NULL fields",
                defaultValue=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        out_path = self.parameterAsFile(parameters, self.TARGET_SQLITE, context)
        threedi_db = get_threedi_database(filename=out_path, feedback=feedback)
        if not threedi_db:
            return {}
        try:
            schema = threedi_db.schema
            schema.validate_schema()

        except errors.MigrationMissingError:
            feedback.pushWarning(
                "The selected 3Di spatialite does not have the latest database schema version. Please migrate this "
                "spatialite and try again: Processing > Toolbox > 3Di > Schematisation > Migrate spatialite"
            )
            return {}

        checks = []

        if parameters[self.MANHOLE_INDICATOR]:
            checks.append("manhole_indicator")

        if parameters[self.PIPE_FRICTION]:
            checks.append("pipe_friction")

        if parameters[self.MANHOLE_AREA]:
            checks.append("manhole_area")

        guesser = guess_indicators_utils.Guesser(threedi_db)
        msg = guesser.run(checks, parameters[self.ONLY_NULL_FIELDS])

        feedback.pushInfo(f"Guess indicators ready: {msg}")

        return {}

    def name(self):
        return "guess_indicators"

    def displayName(self):
        return self.tr("Guess Indicators")

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return "Schematisation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return GuessIndicatorAlgorithm()


class ImportHydXAlgorithm(QgsProcessingAlgorithm):
    """
    Import data from GWSW HydX to a 3Di Spatialite
    """

    INPUT_DATASET_NAME = "INPUT_DATASET_NAME"
    HYDX_DOWNLOAD_DIRECTORY = "HYDX_DOWNLOAD_DIRECTORY"
    INPUT_HYDX_DIRECTORY = "INPUT_HYDX_DIRECTORY"
    TARGET_SQLITE = "TARGET_SQLITE"

    def initAlgorithm(self, config):
        self.addParameter(
            QgsProcessingParameterFile(
                self.TARGET_SQLITE, "Target 3Di Spatialite", extension="sqlite"
            )
        )

        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_HYDX_DIRECTORY,
                "GWSW HydX directory (local)",
                behavior=QgsProcessingParameterFile.Folder,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.INPUT_DATASET_NAME, "GWSW dataset name (online)", optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.HYDX_DOWNLOAD_DIRECTORY,
                "Destination directory for GWSW HydX dataset download",
                optional=True,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        hydx_dataset_name = self.parameterAsString(
            parameters, self.INPUT_DATASET_NAME, context
        )
        hydx_download_dir = self.parameterAsString(
            parameters, self.HYDX_DOWNLOAD_DIRECTORY, context
        )
        hydx_path = self.parameterAsString(
            parameters, self.INPUT_HYDX_DIRECTORY, context
        )
        out_path = self.parameterAsFile(parameters, self.TARGET_SQLITE, context)
        threedi_db = get_threedi_database(filename=out_path, feedback=feedback)
        if not threedi_db:
            raise QgsProcessingException(
                f"Unable to connect to 3Di spatialite '{out_path}'"
            )
        try:
            schema = threedi_db.schema
            schema.validate_schema()

        except errors.MigrationMissingError:
            raise QgsProcessingException(
                "The selected 3Di spatialite does not have the latest database schema version. Please migrate this "
                "spatialite and try again: Processing > Toolbox > 3Di > Schematisation > Migrate spatialite"
            )
        if not (hydx_dataset_name or hydx_path):
            raise QgsProcessingException(
                "Either 'GWSW HydX directory (local)' or 'GWSW dataset name (online)' must be filled in!"
            )
        if hydx_dataset_name and hydx_path:
            feedback.pushWarning(
                "Both 'GWSW dataset name (online)' and 'GWSW HydX directory (local)' are filled in. "
                "'GWSW dataset name (online)' will be ignored. This dataset will not be downloaded."
            )
        elif hydx_dataset_name:
            try:
                hydx_download_path = Path(hydx_download_dir)
                hydx_download_dir_is_valid = hydx_download_path.is_dir()
            except TypeError:
                hydx_download_dir_is_valid = False
            if parameters[self.HYDX_DOWNLOAD_DIRECTORY] == "TEMPORARY_OUTPUT":
                hydx_download_dir_is_valid = True
            if not hydx_download_dir_is_valid:
                raise QgsProcessingException(
                    f"'Destination directory for HydX dataset download' ({hydx_download_path}) is not a valid directory"
                )
            hydx_path = download_hydx(
                dataset_name=hydx_dataset_name,
                target_directory=hydx_download_path,
                wait_times=[0.1, 1, 2, 3, 4, 5, 10],
                feedback=feedback,
            )
            # hydx_path will be None if user has canceled the process during download
            if feedback.isCanceled():
                raise QgsProcessingException("Process canceled")
        feedback.pushInfo(f"Starting import of {hydx_path} to {out_path}")
        log_path = Path(out_path).parent / "import_hydx.log"
        write_logging_to_file(log_path)
        feedback.pushInfo(f"Logging will be written to {log_path}")
        run_import_export(export_type="threedi", hydx_path=hydx_path, out_path=out_path)
        return {}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "import_hydx"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Import GWSW HydX")

    def shortHelpString(self):
        return """
        <h3>Introduction</h3>
        <p>Use this processing algorithm to import data in the format of the Dutch "Gegevenswoordenboek Stedelijk Water (GWSW)". Either select a previously downloaded local dataset, or download a dataset directly from the server.</p>
        <p>A log file will be created in the same directory as the Target 3Di Spatialite. Please check this log file after the import has completed.&nbsp;&nbsp;</p>
        <h3>Parameters</h3>
        <h4>Target 3Di Spatialite</h4>
        <p>Spatialite (.sqlite) file that contains the layers required by 3Di. Imported data will be added to any data already contained in the 3Di Spatialite.</p>
        <h4>GWSW HydX directory (local)</h4>
        <p>Use this option if you have already downloaded a GWSW HydX dataset to a local directory.</p>
        <h4>GWSW dataset name (online)</h4>
        <p>Use this option if you want to download a GWSW HydX dataset.</p>
        <h4>Destination directory for GWSW HydX dataset download</h4>
        <p>If you have chosen to download a GWSW HydX dataset, this is the directory it will be downloaded to.</p>
        """

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return "Schematisation"

    def tr(self, string):
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ImportHydXAlgorithm()
