import logging

from PySide6.QtWidgets import QComboBox

from game.commands import apply_livery, livery_choices
from game.commands.squadrons import LIVERY_SET_TEXT
from game.gamelock import game_lock
from game.squadrons import Squadron


class SquadronLiverySelector(QComboBox):
    """
    A combo box for selecting a squadron's livery.
    The combo box will automatically be populated with all available liveries.
    """

    def __init__(self, squadron: Squadron, update_squadron: bool = True) -> None:
        super().__init__()
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

        self.squadron = squadron
        self.aircraft_type = squadron.aircraft

        if update_squadron:
            self.currentTextChanged.connect(self.on_change)

        with game_lock():
            choices = livery_choices(squadron)
        for choice in choices:
            self.addItem(choice.label, userData=choice.livery_id)
        selected = next((c for c in choices if c.selected), None)
        if selected is not None:
            self.setCurrentText(selected.label)
        if not choices:
            logging.info(f"Liveries for {self.aircraft_type} is empty!")
            self.addItem("No available liveries (using DCS default)")
            self.setEnabled(False)

    @property
    def using_livery_set(self) -> bool:
        return self.currentText() == LIVERY_SET_TEXT

    def on_change(self, text: str) -> None:
        with game_lock():
            apply_livery(self.squadron, self.currentData(), text == LIVERY_SET_TEXT)
