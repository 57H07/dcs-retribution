from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from game.commands import CommandError

from . import (
    airwing,
    applog,
    careers,
    controlpoints,
    debuggeometries,
    downedpilots,
    eventstream,
    flightpayload,
    flights,
    frontlines,
    game,
    gamesettings,
    mapzones,
    missionresult,
    native,
    navmesh,
    packages,
    preferences,
    qt,
    reports,
    supplyroutes,
    tgos,
    unitinfo,
    waypoints,
    iadsnetwork,
    journal,
    tools,
    transfers,
)
from .commanderrors import command_error_handler
from .security import require_api_key
from .settings import ServerSettings

app = FastAPI(dependencies=[Depends(require_api_key)])
app.add_exception_handler(CommandError, command_error_handler)
app.include_router(airwing.router)
app.include_router(controlpoints.router)
app.include_router(debuggeometries.router)
app.include_router(downedpilots.router)
app.include_router(eventstream.router)
app.include_router(flightpayload.router)
app.include_router(flights.router)
app.include_router(frontlines.router)
app.include_router(game.router)
app.include_router(gamesettings.router)
app.include_router(mapzones.router)
app.include_router(missionresult.router)
app.include_router(native.router)
app.include_router(navmesh.router)
app.include_router(packages.router)
app.include_router(preferences.router)
app.include_router(qt.router)
app.include_router(reports.router)
app.include_router(supplyroutes.router)
app.include_router(tgos.router)
app.include_router(unitinfo.router)
app.include_router(waypoints.router)
app.include_router(iadsnetwork.router)
# WEB-08.2: transfers, notes, info panel, careers, logs, about, tools.
app.include_router(applog.router)
app.include_router(careers.router)
app.include_router(journal.router)
app.include_router(tools.router)
app.include_router(transfers.router)


origins = ["file://"]
if ServerSettings.get().cors_allow_debug_server:
    origins.append("http://localhost:3000")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
