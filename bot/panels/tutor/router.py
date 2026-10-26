from aiogram import Router
from bot.panels.tutor.dashboard import router as dashboard_router

tutor_router = Router()
tutor_router.include_router(dashboard_router)
