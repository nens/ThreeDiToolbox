"""Value with automatically attasignal


"""


class ValueWithChangeSignal(object):
    """Value for use inside a BaseModel. A change emits a signal.

    It works like a python property. The whole ``__get__``, ``instance``,
    ``owner`` stuff is explained here:
    https://stackoverflow.com/a/18038707/27401

    The ``signal_setting_name`` has to do with the way project state is saved,
    see ``utils/qprojects.py``.

    """

    def __init__(self, signal_name, signal_setting_name, initial_value=None):
        self.signal_name = signal_name
        self.signal_setting_name = signal_setting_name
        self.value = initial_value

    def __get__(self, instance, owner):
        return self.value

    def __set__(self, instance, value):
        self.value = value
        getattr(instance, self.signal_name).emit(self.signal_setting_name, value)
