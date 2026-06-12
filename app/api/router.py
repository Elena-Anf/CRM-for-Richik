from fastapi import APIRouter

from app.api.routes import appointments, clients, masters, services, pages, payouts, breeds, settings

api_router = APIRouter()

api_router.include_router(pages.router, tags=["pages"])
api_router.include_router(appointments.router, prefix="/api/appointments", tags=["appointments"])
api_router.include_router(clients.router, prefix="/api/clients", tags=["clients"])
api_router.include_router(masters.router, prefix="/api/masters", tags=["masters"])
api_router.include_router(services.router, prefix="/api/services", tags=["services"])
api_router.include_router(payouts.router, prefix="/api/payouts", tags=["payouts"])
api_router.include_router(breeds.router, prefix="/api/breeds", tags=["breeds"])
api_router.include_router(settings.router, prefix="/api/settings", tags=["settings"])
