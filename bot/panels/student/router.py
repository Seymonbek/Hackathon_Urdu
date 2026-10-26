from aiogram import Router
from bot.panels.student import onboarding, feed, applications, internship, profile

router = Router()
router.include_router(onboarding.router)
router.include_router(feed.router)
router.include_router(applications.router)
router.include_router(internship.router)
router.include_router(profile.router)
