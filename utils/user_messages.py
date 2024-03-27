# If you don't include this import the test 'test_set_and_load_list'
# test_project will fail! WTF?
from contextlib import contextmanager
from qgis.core import Qgis
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.utils import iface


def pop_up_info(msg: str = "", title: str = "Information", parent=None):
    """Display an info message via Qt box"""
    QMessageBox.information(parent, title, "%s" % msg)


def pop_up_critical(msg: str = "", title: str = "Critical", parent=None):
    if iface is None:
        return

    """Display an error message via Qt box"""
    QMessageBox.critical(parent, title, msg)


def statusbar_message(msg=""):
    """Display message in status bar"""
    if iface is None:
        return
    iface.mainWindow().statusBar().showMessage(msg)


def messagebar_message(title, msg, level=None, duration=0):
    """Show message in the message bar (just above the map)

    Args:
        title (str): title of messages, showed bold in the start of the message
        msg (str): message
        level (int): INFO = 0, WARNING = 1, CRITICAL = 2, SUCCESS = 3. It is
            possible to use QgsMessage.INFO, etc
        duration (int): how long this the message displays in seconds

    """
    if iface is None:
        return
    if not level:
        level = Qgis.Info
    iface.messageBar().pushMessage(title, msg, level, duration)


def messagebar_pop_message():
    """Remove the currently displayed item from the bar and display the next item in the stack.
       If no remaining items are present, the bar will be hidden."""
    iface.messageBar().popWidget()
    QApplication.processEvents()


def pop_up_question(msg="", title="", parent=None):
    """Message box question (Yes or No).

    Returns:
        True if 'Yes' was clicked, or False if 'No' was clicked.
    """
    reply = QMessageBox.question(
        parent, title, msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No
    )

    return reply == QMessageBox.Yes


class StatusProgressBar(object):
    def __init__(self, maximum=100, message_title=""):

        self.maximum = maximum
        self.message_bar = iface.messageBar().createMessage(message_title, "")

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.message_bar.layout().addWidget(self.progress_bar)
        if iface is not None:
            iface.messageBar().pushWidget(self.message_bar, Qgis.Info)

        self.progress = 0
        iface.mainWindow().repaint()

    def increase_progress(self, steps=1, message=None):

        self.progress += steps
        self.progress_bar.setValue(self.progress)
        if message:
            self.message_bar.setText(message)
        QApplication.processEvents()

    def set_value(self, val, message=None):

        self.progress = val
        self.progress_bar.setValue(self.progress)
        if message:
            self.message_bar.setText(message)
        QApplication.processEvents()

    def __del__(self):
        if iface is not None:
            iface.messageBar().clearWidgets()


@contextmanager
def progress_bar(iface, min_value=1, max_value=100):
    """
    If you want more control over the layout of your progress bar and want
    to be able to add messages to it etc, use the StatusProgressBar object

    usage::

        with progress_bar(iface) as pb:
            pb.setValue(value)

    """
    # clear the message bar
    iface.messageBar().clearWidgets()
    # set a new message bar
    try:
        progressMessageBar = iface.messageBar()

        _progress_bar = QProgressBar()
        # Maximum is set to 100, making it easy to work with
        # percentage of completion
        _progress_bar.setMinimum(min_value)
        _progress_bar.setMaximum(max_value)
        # pass the progress bar to the message Bar
        progressMessageBar.pushWidget(_progress_bar)
        yield _progress_bar
    finally:
        iface.messageBar().clearWidgets()
