from aiogram import Router
from bot.panels.employer import onboarding, post_job, inbox, active_jobs

router = Router()
router.include_router(onboarding.router)
router.include_router(post_job.router)
router.include_router(inbox.router)
router.include_router(active_jobs.router)
