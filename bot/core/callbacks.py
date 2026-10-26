from typing import Optional
from aiogram.filters.callback_data import CallbackData


# TALABA CALLBACKLARI (st:*)
class StudentJobAction(CallbackData, prefix="st_job"):
    action: str  # view, apply, save, withdraw
    job_id: int


class StudentPagination(CallbackData, prefix="st_page"):
    section: str  # feed, my_apps, saved, grants
    page: int


class StudentConfirmAction(CallbackData, prefix="st_conf"):
    action: str  # accept_offer, finish_job, cancel_job
    app_id: int


class StudentSponsorshipAction(CallbackData, prefix="st_spon"):
    action: str  # accept, view_contract
    spon_id: int


# ISH BERUVCHI CALLBACKLARI (emp:*)
class EmployerJobAction(CallbackData, prefix="emp_job"):
    action: str  # view, edit, toggle_status, delete
    job_id: int


class EmployerAppAction(CallbackData, prefix="emp_app"):
    action: str  # accept, reject, backup, no_show, finish
    app_id: int


class EmployerPagination(CallbackData, prefix="emp_page"):
    section: str  # jobs, inbox, candidates
    page: int


class EmployerSponsorshipAction(CallbackData, prefix="emp_spon"):
    action: str  # offer, confirm_payment
    app_id: int


# ADMIN CALLBACKLARI (adm:*)
class AdminVerifyAction(CallbackData, prefix="adm_vfy"):
    target: str  # employer, student, sponsorship
    action: str  # approve, reject, block
    id: int


class AdminPagination(CallbackData, prefix="adm_page"):
    section: str  # dashboard, employers, jobs, reports
    page: int
