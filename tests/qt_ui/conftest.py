import os
from typing import Iterator

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qt_app() -> Iterator[QApplication]:
    """One QApplication for the whole session (Qt allows a single instance).

    A widgets application is also a GUI application, so this serves tests that
    only need fonts or pixmaps as well.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QCoreApplication.instance() or QApplication([])
    assert isinstance(app, QApplication)
    yield app
