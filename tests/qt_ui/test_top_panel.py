from qt_ui.widgets.QTopPanel import QTopPanel


def test_game_is_a_property() -> None:
    # The panel reads self.game.turn etc.; a misplaced decorator made it a plain
    # method and crashed the main window as soon as a game was loaded.
    assert isinstance(QTopPanel.__dict__["game"], property)
    assert not isinstance(QTopPanel.__dict__["refresh_theme_icons"], property)
