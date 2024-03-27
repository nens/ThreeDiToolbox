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
from collections import namedtuple
from processing.gui.wrappers import DIALOG_STANDARD
from processing.gui.wrappers import WidgetWrapper
from qgis.core import QgsFeedback
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingContext
from qgis.core import QgsProcessingException
from qgis.core import QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterEnum
from qgis.core import QgsProcessingParameterFile
from qgis.core import QgsProcessingParameterFileDestination
from qgis.core import QgsProcessingParameterNumber
from qgis.core import QgsProcessingParameterRasterLayer
from qgis.core import QgsProcessingParameterString
from qgis.core import QgsMeshLayer
from qgis.core import QgsRasterLayer
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QCoreApplication
from qgis.PyQt.QtWidgets import QComboBox
from threedidepth.calculate import calculate_waterdepth
from threedidepth.calculate import MODE_CONSTANT
from threedidepth.calculate import MODE_CONSTANT_S1
from threedidepth.calculate import MODE_LINEAR
from threedidepth.calculate import MODE_LIZARD
from threedidepth.calculate import MODE_LIZARD_S1
from threedi_results_analysis.utils.user_messages import pop_up_info

import h5py
import logging
import os
import pathlib


logger = logging.getLogger(__name__)
pluginPath = os.path.split(os.path.dirname(__file__))[0]
Mode = namedtuple("Mode", ["name", "description"])


class ProcessingParameterNetcdfNumber(QgsProcessingParameterNumber):
    def __init__(self, *args, parentParameterName="", optional=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.parentParameterName = parentParameterName
        self.optional = optional
        self.setMetadata({"widget_wrapper": {"class": ThreediResultTimeSliderWidget}})


class ThreediResultTimeSliderWidget(WidgetWrapper):
    def createWidget(self):
        if self.dialogType == DIALOG_STANDARD:
            if not self.parameterDefinition().optional:
                self._widget = TimeSliderWidget()
            else:
                self._widget = CheckboxTimeSliderWidget()
        else:
            self._widget = TimeStepsCombobox()
        return self._widget

    def value(self):
        return self._widget.getValue()

    def postInitialize(self, wrappers):
        # Connect the result-file parameter to the TimeSliderWidget/TimeStepsCombobox
        for wrapper in wrappers:
            if wrapper.parameterDefinition().name() == self.param.parentParameterName:
                wrapper.wrappedWidget().fileChanged.connect(self._widget.new_file_event)


WIDGET, BASE = uic.loadUiType(os.path.join(pluginPath, "processing", "ui", "widgetTimeSlider.ui"))


class TimeSliderWidget(BASE, WIDGET):
    """
    Timeslider form widget. Provide a horizontal slider and an LCD connected to the slider.
    """

    def __init__(self):
        super(TimeSliderWidget, self).__init__(None)
        self.setupUi(self)
        self.horizontalSlider.valueChanged.connect(self.set_lcd_value)
        self.index = None
        self.timestamps = None
        self.reset()

    def getValue(self):
        return self.index

    def set_timestamps(self, timestamps):
        self.setDisabled(False)
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(len(timestamps) - 1)
        self.timestamps = timestamps
        self.set_lcd_value(0)  # also sets self.index

    def set_lcd_value(self, index: int):
        self.index = index
        if self.timestamps is not None:
            value = self.timestamps[index]
        else:
            value = 0
        lcd_value = format_timestep_value(value=value, drop_leading_zero=True)
        self.lcdNumber.display(lcd_value)

    def reset(self):
        self.setDisabled(True)
        self.index = None
        self.timestamps = None
        self.horizontalSlider.setMinimum(0)
        self.horizontalSlider.setMaximum(0)
        self.horizontalSlider.setValue(0)

    def new_file_event(self, file_path):
        """New file has been selected by the user. Try to read in the timestamps from the file."""
        if not file_path or not os.path.isfile(file_path):
            self.reset()
            return

        try:
            with h5py.File(file_path, "r") as results:
                timestamps = results["time"][()]
                self.set_timestamps(timestamps)
        except Exception as e:
            logger.exception(e)
            pop_up_info(msg="Unable to read the file, see the logging for more information.")
            self.reset()


WIDGET, BASE = uic.loadUiType(os.path.join(pluginPath, "processing", "ui", "widgetTimeSliderCheckbox.ui"))


class CheckboxTimeSliderWidget(TimeSliderWidget, WIDGET, BASE):
    """Timeslider widget with a checkbox to enable/disable the timeslider"""

    def __init__(self):
        super().__init__()
        self.horizontalSlider.setDisabled(not self.checkBox.isChecked())
        self.checkBox.stateChanged.connect(self.new_check_box_event)

    def getValue(self):
        if self.checkBox.isChecked():
            return self.index
        else:
            return None

    def new_check_box_event(self, state):
        self.horizontalSlider.setDisabled(not self.checkBox.isChecked())


class TimeStepsCombobox(QComboBox):
    """Combobox with populated timestep data."""

    def getValue(self):
        return self.currentIndex()

    def populate_timestamps(self, timestamps):
        for i, value in enumerate(timestamps):
            human_readable_value = format_timestep_value(value)
            if human_readable_value.startswith("0"):
                human_readable_value = human_readable_value.split(" ", 1)[-1]
            self.addItem(human_readable_value)
        self.setCurrentIndex(0)

    def new_file_event(self, file_path):
        """New file has been selected by the user. Try to read in the timestamps from the file."""
        if not file_path or not os.path.isfile(file_path):
            self.clear()
            return

        try:
            with h5py.File(file_path, "r") as results:
                timestamps = results["time"][()]
                self.populate_timestamps(timestamps)
        except Exception as e:
            logger.exception(e)
            pop_up_info(msg="Unable to read the file, see the logging for more information.")
            self.clear()


class ThreediDepthAlgorithm(QgsProcessingAlgorithm):
    """
    Calculates water depth or water level rasters from 3Di result NetCDF
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    MODES = [
        Mode(MODE_LIZARD, "Interpolated water depth"),
        Mode(MODE_LIZARD_S1, "Interpolated water level"),
        Mode(MODE_CONSTANT, "Non-interpolated water depth"),
        Mode(MODE_CONSTANT_S1, "Non-interpolated water level"),
    ]

    GRIDADMIN_INPUT = "GRIDADMIN_INPUT"
    RESULTS_3DI_INPUT = "RESULTS_3DI_INPUT"
    DEM_INPUT = "DEM_INPUT"
    MODE_INPUT = "MODE_INPUT"
    CALCULATION_STEP_INPUT = "CALCULATION_STEP_INPUT"
    AS_NETCDF_INPUT = "AS_NETCDF_INPUT"
    CALCULATION_STEP_END_INPUT = "CALCULATION_STEP_END_INPUT"
    WATER_DEPTH_LEVEL_NAME = "WATER_DEPTH_LEVEL_NAME"
    OUTPUT_DIRECTORY = "OUTPUT_DIRECTORY"
    WATER_DEPTH_OUTPUT = "WATER_DEPTH_OUTPUT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ThreediDepthAlgorithm()

    def name(self):
        """Returns the algorithm name, used for identifying the algorithm"""
        return "threedidepth"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Water depth/level raster")

    def group(self):
        """Returns the name of the group this algorithm belongs to"""
        return self.tr("Post-process results")

    def groupId(self):
        """Returns the unique ID of the group this algorithm belongs to"""
        return "postprocessing"

    def shortHelpString(self):
        """Returns a localised short helper string for the algorithm"""
        return self.tr("Calculate water depth/level raster for specified timestep")

    def initAlgorithm(self, config=None):
        """Here we define the inputs and output of the algorithm"""
        # Input parameters
        self.addParameter(
            QgsProcessingParameterFile(self.GRIDADMIN_INPUT, self.tr("Gridadmin.h5 file"), extension="h5")
        )
        self.addParameter(
            QgsProcessingParameterFile(self.RESULTS_3DI_INPUT, self.tr("Results_3di.nc file"), extension="nc")
        )
        self.addParameter(QgsProcessingParameterRasterLayer(self.DEM_INPUT, self.tr("DEM")))
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.MODE_INPUT,
                description=self.tr("Interpolation mode"),
                options=[m.description for m in self.MODES],
                defaultValue=MODE_LINEAR,
            )
        )
        self.addParameter(
            ProcessingParameterNetcdfNumber(
                name=self.CALCULATION_STEP_INPUT,
                description=self.tr("The timestep in the simulation for which you want to generate a raster"),
                defaultValue=-1,
                parentParameterName=self.RESULTS_3DI_INPUT,
            )
        )
        self.addParameter(
            ProcessingParameterNetcdfNumber(
                name=self.CALCULATION_STEP_END_INPUT,
                description=self.tr("Last timestep (for multiple timesteps export)"),
                defaultValue=-2,
                parentParameterName=self.RESULTS_3DI_INPUT,
                optional=True,
            )
        )
        self.addParameter(
            QgsProcessingParameterString(
                self.WATER_DEPTH_LEVEL_NAME,
                self.tr("Water depth/level raster name"),
                defaultValue="water_depth_level",
            )
        )
        output_param = QgsProcessingParameterFile(
            self.OUTPUT_DIRECTORY,
            self.tr("Destination folder for water depth/level raster"),
            behavior=QgsProcessingParameterFile.Folder,
        )
        self.addParameter(output_param)
        self.addParameter(
            QgsProcessingParameterBoolean(
                name=self.AS_NETCDF_INPUT,
                description="Export the water depth/level as a NetCDF file (experimental)",
                defaultValue=False,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Create the water depth raster with the provided user inputs
        """
        dem_filename = self.parameterAsRasterLayer(parameters, self.DEM_INPUT, context).source()
        gridadmin_path = parameters[self.GRIDADMIN_INPUT]
        results_3di_path = parameters[self.RESULTS_3DI_INPUT]
        mode_index = self.parameterAsEnum(parameters, self.MODE_INPUT, context)
        step = parameters[self.CALCULATION_STEP_INPUT]
        endstep = parameters[self.CALCULATION_STEP_END_INPUT]
        if endstep:
            if endstep <= step:
                feedback.reportError(
                    "The last timestep should be larger than the first timestep.",
                    fatalError=True,
                )
                return {}
            timesteps = list(range(step, endstep))
        else:
            timesteps = [step]

        raster_filename = parameters[self.WATER_DEPTH_LEVEL_NAME]
        if not raster_filename:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.WATER_DEPTH_LEVEL_NAME))

        output_location = parameters[self.OUTPUT_DIRECTORY]
        if not output_location:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.OUTPUT_DIRECTORY))

        as_netcdf = parameters[self.AS_NETCDF_INPUT]
        raster_extension = "nc" if as_netcdf else "tif"
        raster_filename_with_ext = f"{raster_filename}.{raster_extension}"
        waterdepth_output_file = os.path.join(output_location, raster_filename_with_ext)
        if os.path.isfile(waterdepth_output_file):
            os.remove(waterdepth_output_file)

        try:
            calculate_waterdepth(
                gridadmin_path=gridadmin_path,
                results_3di_path=results_3di_path,
                dem_path=dem_filename,
                waterdepth_path=waterdepth_output_file,
                calculation_steps=timesteps,
                mode=self.MODES[mode_index].name,
                progress_func=Progress(feedback),
                netcdf=as_netcdf,
            )
        except CancelError:
            # When the process is cancelled, we just show the intermediate product
            pass

        if as_netcdf:
            layer = QgsMeshLayer(waterdepth_output_file, raster_filename, "mdal")
        else:
            layer = QgsRasterLayer(waterdepth_output_file, raster_filename)
        context.temporaryLayerStore().addMapLayer(layer)
        layer_details = QgsProcessingContext.LayerDetails(raster_filename, context.project(), self.WATER_DEPTH_OUTPUT)
        context.addLayerToLoadOnCompletion(layer.id(), layer_details)
        return {}


class ThreediMaxDepthAlgorithm(QgsProcessingAlgorithm):
    """
    Calculates maximum water depth or water level rasters from 3Di result NetCDF
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    MODES = [
        Mode(MODE_LIZARD, "Interpolated water depth"),
        Mode(MODE_LIZARD_S1, "Interpolated water level"),
        Mode(MODE_CONSTANT, "Non-interpolated water depth"),
        Mode(MODE_CONSTANT_S1, "Non-interpolated water level"),
    ]

    GRIDADMIN_INPUT = "GRIDADMIN_INPUT"
    RESULTS_3DI_INPUT = "RESULTS_3DI_INPUT"
    DEM_INPUT = "DEM_INPUT"
    MODE_INPUT = "MODE_INPUT"
    OUTPUT_FILENAME = "OUTPUT_FILENAME"
    WATER_DEPTH_OUTPUT = "WATER_DEPTH_OUTPUT"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate("Processing", string)

    def createInstance(self):
        return ThreediMaxDepthAlgorithm()

    def name(self):
        """Returns the algorithm name, used for identifying the algorithm"""
        return "threedidepth_max"

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Maximum water depth/level raster")

    def group(self):
        """Returns the name of the group this algorithm belongs to"""
        return self.tr("Post-process results")

    def groupId(self):
        """Returns the unique ID of the group this algorithm belongs to"""
        return "postprocessing"

    def shortHelpString(self):
        """Returns a localised short helper string for the algorithm"""
        return self.tr("Calculate maximum water depth/level raster over all timesteps")

    def initAlgorithm(self, config=None):
        """Here we define the inputs and output of the algorithm"""
        # Input parameters
        self.addParameter(
            QgsProcessingParameterFile(self.GRIDADMIN_INPUT, self.tr("Gridadmin.h5 file"), extension="h5")
        )
        self.addParameter(
            QgsProcessingParameterFile(self.RESULTS_3DI_INPUT, self.tr("Results_3di.nc file"), extension="nc")
        )
        self.addParameter(QgsProcessingParameterRasterLayer(self.DEM_INPUT, self.tr("DEM")))
        self.addParameter(
            QgsProcessingParameterEnum(
                name=self.MODE_INPUT,
                description=self.tr("Interpolation mode"),
                options=[m.description for m in self.MODES],
                defaultValue=MODE_LINEAR,
            )
        )
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_FILENAME,
                self.tr("Destination file path for water depth/level raster"),
                fileFilter="*.tif",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        """
        Create the water depth raster with the provided user inputs
        """
        dem_filename = self.parameterAsRasterLayer(parameters, self.DEM_INPUT, context).source()
        gridadmin_path = parameters[self.GRIDADMIN_INPUT]
        results_3di_path = parameters[self.RESULTS_3DI_INPUT]
        mode_index = self.parameterAsEnum(parameters, self.MODE_INPUT, context)

        waterdepth_output_file = parameters[self.OUTPUT_FILENAME]
        if not waterdepth_output_file:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.OUTPUT_FILENAME))

        layer_name = pathlib.Path(waterdepth_output_file).stem

        if os.path.isfile(waterdepth_output_file):
            os.remove(waterdepth_output_file)

        try:
            calculate_waterdepth(
                gridadmin_path=gridadmin_path,
                results_3di_path=results_3di_path,
                dem_path=dem_filename,
                waterdepth_path=waterdepth_output_file,
                calculate_maximum_waterlevel=True,
                mode=self.MODES[mode_index].name,
                progress_func=Progress(feedback),
            )
        except CancelError:
            # When the process is cancelled, we just show the intermediate product
            pass

        layer = QgsRasterLayer(waterdepth_output_file, layer_name)
        context.temporaryLayerStore().addMapLayer(layer)
        layer_details = QgsProcessingContext.LayerDetails(layer_name, context.project(), self.WATER_DEPTH_OUTPUT)
        context.addLayerToLoadOnCompletion(layer.id(), layer_details)
        return {}


class CancelError(Exception):
    """Error which gets raised when a user presses the 'cancel' button"""


class Progress:
    def __init__(self, feedback: QgsFeedback):
        self.feedback = feedback

    def __call__(self, progress: float):
        self.feedback.setProgress(progress * 100)
        if self.feedback.isCanceled():
            raise CancelError()


def format_timestep_value(value: float, drop_leading_zero: bool = False) -> str:
    days, seconds = divmod(int(value), 24 * 60 * 60)
    hours, seconds = divmod(seconds, 60 * 60)
    minutes, seconds = divmod(seconds, 60)

    if days == 0 and drop_leading_zero:
        formatted_display = "{:02d}:{:02d}".format(hours, minutes)
        return formatted_display

    formatted_display = "{:d} {:02d}:{:02d}".format(days, hours, minutes)
    return formatted_display
