# (c) Nelen & Schuurmans, see LICENSE.rst.

from ThreeDiToolbox.tool_commands.base.custom_command import CustomCommandBase
from ThreeDiToolbox.utils.threedi_database import ThreediDatabase
from ThreeDiToolbox.utils.user_messages import messagebar_message
from tool_commands.raster_checker.raster_checker_dialog import RasterCheckerDialogWidget
from tool_commands.raster_checker.raster_checker_main import RasterChecker

import inspect
import logging


logger = logging.getLogger(__name__)


class CustomCommand(CustomCommandBase):
    class Fields(object):
        name = "Raster Checker script"

    def __init__(self, **kwargs):
        self._fields = sorted(
            [
                (name, cl)
                for name, cl in inspect.getmembers(
                    self.Fields, lambda a: not (inspect.isroutine(a))
                )
                if not name.startswith("__") and not name.startswith("_")
            ]
        )
        self.iface = kwargs.get("iface")
        self.ts_datasource = kwargs.get("ts_datasource")
        self.tool_dialog_widget = None

    def run(self):
        self.show_gui()

    def show_gui(self):
        checks = []
        self.tool_dialog_widget = RasterCheckerDialogWidget(checks=checks, command=self)
        self.tool_dialog_widget.exec_()  # block execution

    def run_it(self, action_list, db_set, db_type):
        db = ThreediDatabase(db_set, db_type)
        checker = RasterChecker(db)
        msg = checker.run(action_list)
        messagebar_message("Raster checker ready", msg, duration=3)
        logger.info("Raster checker ready")
