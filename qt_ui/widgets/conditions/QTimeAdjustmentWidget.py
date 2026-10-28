from typing import Optional

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QHBoxLayout, QDateTimeEdit

from qt_ui.widgets.conditions.QTimeTurnWidget import QTimeTurnWidget
from qt_ui.theme_manager import set_style_class


class QTimeAdjustmentWidget(QWidget):
    def __init__(
        self, time_turn: QTimeTurnWidget, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self.current_datetime = time_turn.sim_controller.current_time_in_sim
        self.init_ui()

    def init_ui(self) -> None:
        vbox = QVBoxLayout()

        vbox.addWidget(QLabel("<h2><b>Time & Date:</b></h2>"))
        warning = QLabel(
            "<h4><b>WARNING: CHANGING TIME/DATE WILL RE-INITIALIZE THE TURN</b></h4>"
        )
        set_style_class(warning, "text-warning")
        vbox.addWidget(warning)

        hbox = QHBoxLayout()

        t = self.current_datetime.time()
        d = self.current_datetime.date()
        self.datetime_edit = QDateTimeEdit(
            QDateTime(d.year, d.month, d.day, t.hour, t.minute, t.second)
        )
        hbox.addWidget(self.datetime_edit)

        vbox.addLayout(hbox)

        self.setLayout(vbox)
