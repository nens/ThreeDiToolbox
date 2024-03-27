from logging import getLogger
from datetime import timedelta as Timedelta
from datetime import datetime as Datetime

from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtCore import pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QDockWidget
from qgis.core import QgsDateTimeRange
from qgis.core import QgsInterval
from qgis.core import QgsTemporalNavigationObject
from qgis.utils import iface

import numpy as np

from threedi_results_analysis.threedi_plugin_model import ThreeDiResultItem


logger = getLogger(__name__)


class TemporalManager(QObject):
    """
    Manager for the temporal controller. Responsibilities:

    When the result set changes or the `align starts` option is modified:
        - Configure appropriate temporal controller extent

    When the temporal range is changed:
        - Update the texts and relative times on all ThreediResultItems
        - Emit a signal for connected tools
    """
    updated = pyqtSignal()

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.temporal_controller = iface.mapCanvas().temporalController()
        self.temporal_controller.updateTemporalRange.connect(self._update)

        self._configuring = False
        self._align_starts = True

    def _update_result(self, result_item, controller_current):
        """
        Update result
        """
        threedi_result = result_item.threedi_result
        result_begin = Datetime.fromisoformat(threedi_result.dt_timestamps[0])
        result_end = Datetime.fromisoformat(threedi_result.dt_timestamps[-1])

        # "de-align" the controller time for this result
        if self._align_starts:
            controller_begin = self.temporal_controller.temporalExtents().begin().toPyDateTime()
            current = controller_current + (result_begin - controller_begin)
        else:
            current = controller_current

        # clip current between result limits
        current = max(result_begin, min(result_end, current))

        # update result item
        result_item._timedelta = current - result_begin
        self.model.set_time_item(result_item)

    def _update(self, qgs_dt_range):
        if self._configuring:
            return

        try:
            current = qgs_dt_range.begin().toPyDateTime()
        except ValueError:
            logger.info('Could not convert animation datetime to python.')
            return

        for result_item in self.model.get_results(checked_only=False):
            self._update_result(
                result_item=result_item, controller_current=current,
            )

        logger.info("Updating temporal controller")
        self.updated.emit()

    @pyqtSlot(bool)
    def set_align_starts(self, align):
        self._align_starts = align
        self.configure()

    @pyqtSlot(ThreeDiResultItem)
    def configure(self, result_item=None):
        logger.info("Configuring temporal controller")

        results = self.model.get_results(checked_only=False)
        if not results:
            return

        # make temporal controller widget visible
        for dock_widget in iface.mainWindow().findChildren(QDockWidget):
            if dock_widget.objectName() == 'Temporal Controller':
                dock_widget.setVisible(True)

        # gather info
        threedi_results = [r.threedi_result for r in results]
        datetimes = [
            np.array(tr.dt_timestamps, dtype='datetime64[s]')
            for tr in threedi_results
        ]

        # frame duration
        intervals = [
            round((d[1:] - d[:-1]).min().item().total_seconds())
            for d in datetimes
            if d.size >= 2
        ]
        frame_duration = max(1, min(intervals)) if intervals else 1
        logger.info(f"frame_duration {frame_duration}")

        # extent
        start_time = min(d[0].item() for d in datetimes)
        if self._align_starts:
            end_time = start_time + max(d.ptp().item() for d in datetimes)
        else:
            end_time = max(d[-1].item() for d in datetimes)
        end_time += Timedelta(seconds=frame_duration)  # to access last step
        temporal_extents = QgsDateTimeRange(start_time, end_time, True, True)
        logger.info(f"start_time {start_time}")
        logger.info(f"end_time {end_time}")

        # we cannot block the signals from the controller because its widget
        # relies on those signals to update its UI elements
        self._configuring = True
        self.temporal_controller.setNavigationMode(QgsTemporalNavigationObject.NavigationMode.Animated)
        self.temporal_controller.setFrameDuration(QgsInterval(frame_duration))
        self.temporal_controller.setTemporalExtents(temporal_extents)
        self.temporal_controller.rewindToStart()
        self._configuring = False
        self.temporal_controller.skipToEnd()
