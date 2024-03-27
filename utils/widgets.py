from PyQt5.QtGui import QPainter, QPen
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QWidget
from qgis.PyQt.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class PenStyleWidget(QWidget):
    """A simple widget than can be used to display examples of pen styles"""
    def __init__(
        self,
        pen_style: Qt.PenStyle,
        pen_color: QColor,
        parent : QWidget,
    ):
        super().__init__(parent)
        self.pen_style = pen_style
        self.pen_color = pen_color
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, event):
        qp = QPainter(self)
        qp.begin(self)
        pen = QPen(self.pen_color, 2, self.pen_style)
        qp.setPen(pen)
        qp.drawLine(round(0.1*self.width()), round(self.height()/2.0), round(0.9*self.width()), round(self.height()/2.0))
        qp.end()
