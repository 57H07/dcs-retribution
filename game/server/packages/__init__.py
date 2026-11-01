from .radioroutes import router as radio_router
from .routes import router

router.include_router(radio_router)
