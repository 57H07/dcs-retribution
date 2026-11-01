from .flightsettingsroutes import router as flight_settings_router
from .routes import router

router.include_router(flight_settings_router)
