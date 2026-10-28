from PySide6 import QtCore, QtGui
from PySide6.QtWidgets import QCalendarWidget

from qt_ui.theme_manager import theme_signals, token_color


class QLiberationCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super(QLiberationCalendar, self).__init__(parent)
        self.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.setGridVisible(False)
        self.refresh_theme_colors()
        theme_signals().theme_changed.connect(self.refresh_theme_colors)

    def refresh_theme_colors(self, _variant: str = "") -> None:
        # Overrride default QCalendar behaviour that is rendering week end days in red
        for d in (
            QtCore.Qt.DayOfWeek.Monday,
            QtCore.Qt.DayOfWeek.Tuesday,
            QtCore.Qt.DayOfWeek.Wednesday,
            QtCore.Qt.DayOfWeek.Thursday,
            QtCore.Qt.DayOfWeek.Friday,
            QtCore.Qt.DayOfWeek.Saturday,
            QtCore.Qt.DayOfWeek.Sunday,
        ):
            fmt = self.weekdayTextFormat(d)
            fmt.setForeground(token_color("color-text-secondary"))
            self.setWeekdayTextFormat(d, fmt)

    def paintCell(self, painter, rect, date):
        if date == self.selectedDate():
            painter.save()
            painter.fillRect(rect, token_color("color-bg-sunken"))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(token_color("color-accent-default"))
            r = QtCore.QRect(
                QtCore.QPoint(), min(rect.width(), rect.height()) * QtCore.QSize(1, 1)
            )
            r.moveCenter(rect.center())
            painter.drawEllipse(r)
            painter.setPen(QtGui.QPen(token_color("color-text-on-accent")))
            painter.drawText(rect, QtCore.Qt.AlignmentFlag.AlignCenter, str(date.day()))
            painter.restore()
        else:
            super(QLiberationCalendar, self).paintCell(painter, rect, date)
