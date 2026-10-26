from aiogram import Router
from bot.panels.admin import dashboard, employers_mod, export, admin_management

router = Router()
router.include_router(dashboard.router)
router.include_router(employers_mod.router)
router.include_router(export.router)
router.include_router(admin_management.router)
