from pyqtgraph import AxisItem
from qgis.PyQt.QtCore import Qt


class RotateLabelAxisItem(AxisItem):
    """
    Extends AxisItem to draw labels with an angle.

    Useful when using long text-labels which will otherwise overlap, for
    example in a bar-graph.

    Currently only properly supported for the 'bottom' axis orientation.
    """

    def __init__(self, angle=15, *args, **kwargs):
        """
        Initialize an new RotateLabelAxe with provided angle.

        RotateLabelAxe is a subclass of AxisItem. Other args and kwargs are
        passed on to AxisItem. For more information, see
        pyqtgraph.graphicsItems.AxisItem.

        Args:
            angle: (int) angle of the labels, defaults to 15.
            *args:
            **kwargs:
        """
        self.angle = angle
        AxisItem.__init__(self, *args, **kwargs)

    def boundingRect(self):
        # make big outer labels survive to the drawPicture() phase
        return super().boundingRect().adjusted(-500, 0, 500, 0)

    def drawPicture(self, p, axisSpec, tickSpecs, textSpecs):
        p.setRenderHint(p.Antialiasing, False)
        p.setRenderHint(p.TextAntialiasing, True)

        # draw long line along axis
        pen, p1, p2 = axisSpec
        p.setPen(pen)
        p.drawLine(p1, p2)
        p.translate(0.5, 0)  # resolves some damn pixel ambiguity

        # draw ticks
        for pen, p1, p2 in tickSpecs:
            p.setPen(pen)
            p.drawLine(p1, p2)

        # Draw all text
        if self.style["tickFont"] is not None:
            p.setFont(self.style["tickFont"])
        p.setPen(self.pen())

        text_flags = Qt.TextDontClip | Qt.AlignLeft | Qt.AlignTop
        for rect, flags, text in textSpecs:
            p.save()
            p.translate(rect.center())
            p.rotate(self.angle)
            p.scale(0.9, 0.9)
            p.translate(-rect.center())
            rect.setX(rect.center().x())
            p.drawText(rect, text_flags, text)
            p.restore()
