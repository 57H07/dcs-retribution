from .flightsettingsroutes import router as flight_settings_router
from .radioroutes import router as radio_router
from .routes import router

router.include_router(flight_settings_router)
router.include_router(radio_router)
