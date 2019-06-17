# (c) Nelen & Schuurmans, see LICENSE.rst.

from ThreeDiToolbox.tool_commands.custom_command_base import CustomCommandBase
from ThreeDiToolbox.tool_commands.import_sufhyd.import_sufhyd_dialog import (
    ImportSufhydDialogWidget,
)
from ThreeDiToolbox.tool_commands.import_sufhyd.import_sufhyd_main import Importer
from ThreeDiToolbox.utils.threedi_database import ThreediDatabase

import inspect
import logging


logger = logging.getLogger(__name__)


class CustomCommand(CustomCommandBase):
    """
    Things to note:

    If you select a memory layer the behaviour will be different from clicking
    on a normal spatialite view. For example, NcStatsAgg will be used instead
    of NcStats.
    """

    class Fields(object):
        name = "Import sufhyd"
        value = 1

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
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
        self.ts_datasources = kwargs.get("ts_datasources")
        self.tool_dialog_widget = None

    def run(self):
        self.show_gui()

    def show_gui(self):

        self.tool_dialog_widget = ImportSufhydDialogWidget(
            iface=self.iface, ts_datasources=self.ts_datasources, command=self
        )
        self.tool_dialog_widget.exec_()  # block execution

    def run_it(self, sufhyd_file, db_set, db_type):

        # todo: check if database is empty, otherwise popup

        db = ThreediDatabase(db_set, db_type)
        importer = Importer(sufhyd_file, db)
        importer.run_import()

        # todo: show logging
