"""Career page of a player pilot (PER-03.4).

The web UI has its own career screen (WEB-08.2, `/career`); this dialog stays for
the Qt air wing dialog until that one is migrated. The text comes from
`game.squadrons.careerreport`, shared with the web screen.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from game.squadrons.career import Career
from game.squadrons.careerreport import (
    AWARD_HEADERS,
    HISTORY_HEADERS,
    award_rows,
    format_date,
    format_duration,
    history_rows,
    totals,
)

__all__ = [
    "AWARD_HEADERS",
    "CareerDialog",
    "HISTORY_HEADERS",
    "award_rows",
    "format_date",
    "format_duration",
    "history_rows",
    "totals",
]


def _table(headers: list[str], rows: list[list[str]]) -> QTableWidget:
    table = QTableWidget(len(rows), len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    for row, values in enumerate(rows):
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(value))
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(True)
    return table


class CareerDialog(QDialog):
    """Logbook totals, rank, decorations and per-mission history of a pilot."""

    def __init__(self, career: Career, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        pilot = career.pilot
        record = career.logbook
        self.setWindowTitle(f"Career of {pilot.name}")
        self.setMinimumSize(900, 600)

        layout = QVBoxLayout()
        self.setLayout(layout)

        rank = record.rank.name if record.rank is not None else "No rank yet"
        title = QLabel(f"<h2>{rank} {pilot.name}</h2>")
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)
        layout.addWidget(QLabel(f"{career.squadron} - {pilot.status.value}"))

        top = QHBoxLayout()
        layout.addLayout(top)

        totals_box = QGroupBox("Logbook")
        totals_form = QFormLayout()
        totals_box.setLayout(totals_form)
        for label, value in totals(record):
            totals_form.addRow(label, QLabel(value))
        top.addWidget(totals_box)

        awards_box = QGroupBox("Ranks and decorations")
        awards_layout = QVBoxLayout()
        awards_box.setLayout(awards_layout)
        if record.awards:
            self.awards_table = _table(AWARD_HEADERS, award_rows(record.awards))
            awards_layout.addWidget(self.awards_table)
        else:
            awards_layout.addWidget(
                QLabel("Ranks and decorations are awarded after each mission.")
            )
        top.addWidget(awards_box, stretch=1)

        history_box = QGroupBox(f"Mission history ({len(record.logbook)})")
        history_layout = QVBoxLayout()
        history_box.setLayout(history_layout)
        self.history_table = _table(HISTORY_HEADERS, history_rows(record.logbook))
        history_layout.addWidget(self.history_table)
        layout.addWidget(history_box, stretch=1)
