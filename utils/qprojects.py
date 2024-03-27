# (c) Nelen & Schuurmans, see LICENSE.rst.

from io import IOBase
from qgis.core import QgsProject, QgsVectorLayer, QgsMapLayer

import logging
import os


logger = logging.getLogger()


def set_read_only(layer: QgsVectorLayer, enable: bool) -> bool:
    """Marks the layer as readonly, but also removes the Removable flag"""
    if not layer.setReadOnly(enable):
        logger.error("Unable to set layer to read-only")
        return False

    if enable:
        layer.setFlags(QgsMapLayer.Searchable | QgsMapLayer.Identifiable)
    else:
        layer.setFlags(QgsMapLayer.Searchable | QgsMapLayer.Identifiable | QgsMapLayer.Removable)

    return True


class ProjectStateMixin(object):
    """class mixin for writing and loading states of tools to the Qgis Project
    files (``*.qgs``). Expects a class with:

    - an array of tools (self.tools)
    - in QgsInterface available under self.iface

    the tool classes needs the functions and signals:

    - function 'get_state_description(self)': returns tuple with:

        - tool name
        - dictionary with stored setting keys and value types as value
          (supported are int, float, str, bool and list).
          Example::

                def get_state_description(self):
                    return ('result_selection',
                            {
                                'model_schematisation': str,
                                'result_directories': list
                            })

    - function 'set_state(self, settings_dict)': function must update state
      according to state values in dictionary.
      Example (which uses json to serialize more complex objects)::

                def set_state(self, setting_dict):
                    self.datasource.reset()

                    self.datasource.model_spatialite_filepath = \
                            setting_dict.get('model_schematisation', None)

                    result_list = setting_dict.get('result_directories', None)
                    if result_list is not None:
                        for result_json in result_list:
                            result = json.JSONDecoder().decode(result_json)
                            self.ts_datasources.insertRows([result])

    - signal 'state_changed'[str, str, list]: this signal has to emit every
      time a setting which is stored in the state changed. This signal is
      emitted with the parameters:

        - tool name
        - setting key
        - new value. The value is rapped in an extra list (is easier to
          support the different value types through the same signal (
          overloading is supported from qt 4.11.x, so not in Qgis)

          The signal could be declared by adding the next line to the class (
          needs to be an QObject or simular)::

                state_changed = pyqtSignal([str, str, list])

          The signal could be emitted from a function, an example (also wrapping
          a more complex object in json) of this function is::

            def on_state_changed(self, setting_key, value):

                if setting_key == 'result_directories':
                    output = []
                    for result in value:
                        output.append(json.JSONEncoder().encode({
                            'active': result.active.value,
                            'name': result.name.value,
                            'file_path': result.file_path.value,
                            'type': result.type.value
                        }))
                else:
                    output = value

                self.state_changed.emit('result_selection', setting_key,
                                        [output])

    The class with the mixin needs to call the functions:

    - self.init_state_sync() to start the sync
    - self.unload_state_sync() on unload

    Under developement notes:
    The functionality to support relative paths is developed, but because the
    correct signal 'changeHomePath' is supported from 2.17.0, the absolute
    paths are still communicated (in many cases it works, but with new
    projects, the behaviour was still not the same at all circumstances)..

    """

    connect_to_save_and_load = False

    def unload_state_sync(self):
        """removes the connection to signals"""
        for tool in self.tools:
            if hasattr(tool, "set_state"):
                # add listener
                tool.state_changed.connect(self.save_setting_to_project)
        # add listeners to load projects
        if self.connect_to_save_and_load:
            self.iface.newProjectCreated.disconnect(self.load_and_set_state)
            self.iface.projectRead.disconnect(self.load_and_set_state)
            QgsProject.instance().writeProject.disconnect(self.set_paths_relative)
            # TODO: this signal will be available in version 2.17
            # QgsProject.instance().homePathChanged.disconnect(self.set_paths_relative)
            self.connect_to_save_and_load = False

    def init_state_sync(self, connect_to_save_and_load=True):
        """loads and set the state for m the current project and set the
            connection to the required signals from the tools and iface
            interface

        Args:
            connect_to_save_and_load (bool): also include listeners to save,
            clear and load of project files. Made optional, because tests
            don't have full iface interface.
        """
        self.load_and_set_state()
        self.file_dict = {}
        for tool in self.tools:
            if hasattr(tool, "set_state"):
                # add listener
                tool.state_changed.connect(self.save_setting_to_project)
                # keep list of  settings with type 'file', so we can change
                # them when the location and with that the relative paths
                # change
                tool_name, description = tool.get_state_description()
                for key, value in list(description.items()):
                    if isinstance(value, IOBase):
                        tool_key = self.get_tool_state_name(tool_name)
                        if tool_key not in self.file_dict:
                            self.file_dict[tool_key] = {}
                        self.file_dict[tool_key][key] = None

        if connect_to_save_and_load:
            # add listeners to load projects
            self.iface.newProjectCreated.connect(self.load_and_set_state)
            self.iface.projectRead.connect(self.load_and_set_state)
            QgsProject.instance().writeProject.connect(self.set_paths_relative)
            # todo: this signal will be available in version 2.17
            # QgsProject.instance().homePathChanged.connect(self.set_paths_relative)
            self.connect_to_save_and_load = True

    def set_paths_relative(self):
        # todo: save setting which indicates if project is stored relative or
        # absolute,if setting is not set, popup the first time this functions
        # is called
        proj = QgsProject.instance()
        for tool_key, key_dict in list(self.file_dict.items()):
            for setting_key in list(key_dict.keys()):
                value, valid = proj.readEntry(tool_key, "abs_" + setting_key)
                if valid and len(value) > 0:
                    rel_path = self._get_relative_path(value)
                    proj.writeEntry(tool_key, setting_key, rel_path)

    def _get_relative_path(self, file_path):
        proj = QgsProject.instance()
        home = proj.homePath()
        if len(str(home)) > 0:
            rel_path = os.path.relpath(file_path, home)
        else:
            rel_path = file_path
        return rel_path

    def _get_abs_path(self, file_path):
        proj = QgsProject.instance()
        home = proj.homePath()
        abs_path = os.path.normpath(os.path.join(home, file_path))
        return abs_path

    def load_and_set_state(self):
        """loads state from project and sets state on each tool"""
        for tool in self.tools:
            if hasattr(tool, "set_state"):
                # set_initial state
                settings = {}
                tool_name, description = tool.get_state_description()
                name = self.get_tool_state_name(tool_name)
                for key, value_type in list(description.items()):
                    # use string or list reader and transform values ourselves.
                    # QgsProject also has methods to read other value type, but
                    # because 'valid' is (seems to be) always True, it is not
                    # possible to see if the returned value is the real value
                    # or the default. Now the default value is detected by
                    # indetification of an empty string.
                    if value_type == list:
                        value, valid = QgsProject.instance().readListEntry(name, key)
                    else:
                        value, valid = QgsProject.instance().readEntry(name, key)
                        # self.load_func[value.__name__](name, key)
                        if valid and len(value) > 0:
                            if value_type == int:
                                value = int(value)
                            elif value_type == float:
                                value = float(value)
                            elif value_type == bool:
                                value, valid = QgsProject.instance().readBoolEntry(
                                    name, key
                                )
                            elif isinstance(value_type, IOBase):
                                # TODO: change this code when starting to
                                # work with 2.17 and up
                                value, valid = QgsProject.instance().readEntry(
                                    name, "abs_" + key
                                )
                                # value = self._get_abs_path(value)
                        else:
                            value = None

                    settings[key] = value

                tool.set_state(settings)

    def get_tool_state_name(self, tool_name):
        """generate key for specific tool

        Args:
            tool_name (str): unique name of tool within the plugin

        Returns:
            (str) combination of pluginname and toolname to get an unique key
            for storing the state in the QgsProject

        """
        return "threedi_toolbox" + tool_name

    def save_setting_to_project(self, tool_name, key, value_list):
        """sets single setting to QgsProject

        Args:
            tool_name (str): within plugin unique tool name, used as
                key for storage of state
            key (str): key of state setting
            value_list (list): an in a list wrapped state value. Wrapping in
                a list is done to have an uniform type to pass through a signal
        """
        if len(value_list) == 0:
            value = None
        else:
            value = value_list[0]

        name = self.get_tool_state_name(tool_name)

        if isinstance(value, float):
            QgsProject.instance().writeEntryDouble(name, key, value)
        else:
            if name in self.file_dict:
                if key in self.file_dict[name]:
                    # type is file, store absolute path under extra key and
                    # relative path under original key
                    QgsProject.instance().writeEntry(name, "abs_" + key, value)
                    try:
                        value = self._get_relative_path(value)
                    except ValueError:
                        logger.exception(
                            "Could not create relative path from %s, "
                            "leaving the value as-is",
                            value,
                        )

            QgsProject.instance().writeEntry(name, key, value)
