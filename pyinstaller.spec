# -*- mode: python -*-

block_cipher = None

# The shell is only a window with a web view (ADR 0002): PySide6 ships far more.
# Check the package on screen, dialogs included, after updating Qt: a module missing
# here only shows when the package runs.
QT_DLLS = {
    "Qt6Core", "Qt6Gui", "Qt6Network", "Qt6OpenGL", "Qt6Positioning",
    "Qt6PrintSupport", "Qt6Qml", "Qt6QmlMeta", "Qt6QmlModels", "Qt6QmlWorkerScript",
    "Qt6Quick", "Qt6QuickWidgets", "Qt6Svg", "Qt6WebChannel", "Qt6WebChannelQuick",
    "Qt6WebEngineCore", "Qt6WebEngineQuick", "Qt6WebEngineWidgets", "Qt6Widgets",
}
QT_BINDINGS = {
    "QtCore", "QtGui", "QtNetwork", "QtPrintSupport", "QtWebChannel",
    "QtWebEngineCore", "QtWebEngineWidgets", "QtWidgets",
}


def is_unused_qt_file(entry):
    path = entry[0].replace("\\", "/")
    if not path.startswith("PySide6/"):
        return False
    relative = path[len("PySide6/"):]
    name = relative.rsplit("/", 1)[-1]
    stem = name.split(".")[0]
    if relative.startswith("qml/") or relative == "opengl32sw.dll":
        return True
    if relative.startswith("resources/"):
        return "devtools" in name or ".debug." in name
    if relative.startswith("translations/"):
        return name != "en-US.pak"
    if "/" in relative:
        return False
    if stem.startswith("Qt6") and name.endswith(".dll"):
        return stem not in QT_DLLS
    if stem.startswith("Qt") and name.endswith(".pyd"):
        return stem not in QT_BINDINGS
    return False


analysis = Analysis(
    ['./qt_ui/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('resources/caucasus.p', 'dcs/terrain/'),
        ('resources/nevada.p', 'dcs/terrain/'),
        ('client/build', 'client/build'),
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
analysis.binaries = [e for e in analysis.binaries if not is_unused_qt_file(e)]
analysis.datas = [e for e in analysis.datas if not is_unused_qt_file(e)]
pyz = PYZ(
    analysis.pure,
    analysis.zipped_data,
    cipher=block_cipher,
)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    icon="resources/icon.ico",
    exclude_binaries=True,
    name='retribution_main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    contents_directory='.'
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    strip=False,
    upx=True,
    name='dcs-retribution',
)
