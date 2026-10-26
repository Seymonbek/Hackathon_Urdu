import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.core.i18n import get_i18n, get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.students_repo import StudentsRepo
from bot.db.repositories.applications_repo import ApplicationsRepo
from bot.db.repositories.internship_repo import InternshipRepo

router = Router()


class InternshipLogStates(StatesGroup):
    hours = State()
    tasks = State()


@router.message(F.text.in_(get_button_variants("BTN_STUDENT_INTERNSHIP")))
@router.callback_query(F.data == "profile_internship_diary")
async def show_internship_diary(event):
    msg = event.message if isinstance(event, CallbackQuery) else event
    user_id = event.from_user.id
    if isinstance(event, CallbackQuery):
        await event.answer()

    lang = await UsersRepo.get_user_lang(user_id)
    t = get_i18n(lang)

    student = await StudentsRepo.get_by_tg_id(user_id)
    if not student:
        await msg.answer(t.MSG_PLEASE_REGISTER, parse_mode="HTML")
        return

    total_hours = await InternshipRepo.get_total_hours(student["id"])
    logs = await InternshipRepo.get_logs_by_student(student["id"])

    text = (
        f"📜 <b>Elektron Davlat Amaliyoti Kundaligi</b>\n\n"
        f"🎓 <b>Talaba:</b> {html.escape(str(student.get('full_name')))} ({html.escape(str(student.get('major')))})\n"
        f"⏱ <b>Tasdiqlangan amaliyot soatlari:</b> <b>{total_hours} soat</b>\n\n"
        f"📋 <b>Oxirgi yozuvlar:</b>\n"
    )
    empty_note = "Hozircha amaliyot yozuvlari kiritilmagan.\n"
    btn_add = "✍️ Bugungi amaliyotni yozish"

    if logs:
        for l in logs[:5]:
            status = "✅ Tasdiqlangan" if l.get("verified_by_mentor") else "⏳ Kutilmoqda"
            score_text = f" (Baho: {l.get('mentor_score')}⭐)" if l.get("mentor_score") else ""
            text += f"• {l.get('visit_date')} — {l.get('hours_spent')} soat | {status}{score_text}\n  Vazifa: <i>{html.escape(str(l.get('tasks_performed')))}</i>\n"
    else:
        text += empty_note

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=btn_add, callback_data="add_internship_log"),
            ],
            [
                InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="close_carousel"),
            ]
        ]
    )

    await msg.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "add_internship_log")
async def start_add_log(call: CallbackQuery, state: FSMContext):
    lang = await UsersRepo.get_user_lang(call.from_user.id)
    student = await StudentsRepo.get_by_tg_id(call.from_user.id)
    active_app = await ApplicationsRepo.get_active_by_student(student["id"])
    if not active_app:
        err_msg = "Sizda faol amaliyot mavjud emas."
        await call.answer(err_msg, show_alert=True)
        return

    await state.update_data(app_id=active_app["id"], student_id=student["id"], lang=lang)
    await state.set_state(InternshipLogStates.hours)
    await call.answer()
    
    prompt = "Bugun amaliyotda necha soat bo'ldingiz? (Masalan: 3 yoki 4.5):"
    await call.message.answer(prompt, parse_mode="HTML")


@router.message(InternshipLogStates.hours, F.text)
async def process_log_hours(msg: Message, state: FSMContext):
    try:
        hours = float(msg.text.replace(",", ".").strip())
    except ValueError:
        hours = 3.0
    await state.update_data(hours=hours)
    await state.set_state(InternshipLogStates.tasks)
    
    prompt = "Bugun qanday vazifalarni bajardingiz? Qisqacha yozing:\n<i>(Masalan: Sud majlisida kotibga da'vo arizalarini ro'yxatga olishda yordam berdim)</i>"
    await msg.answer(prompt, parse_mode="HTML")


@router.message(InternshipLogStates.tasks, F.text)
async def process_log_tasks(msg: Message, state: FSMContext):
    tasks = msg.text.strip()
    data = await state.get_data()
    from datetime import date

    await InternshipRepo.add_log(
        application_id=data["app_id"],
        student_id=data["student_id"],
        visit_date=str(date.today()),
        hours_spent=data["hours"],
        tasks_performed=tasks,
    )

    await state.clear()
    reply = (
        "✅ <b>Kundalik muvaffaqiyatli saqlandi!</b>\n"
        "Tashkilot mas'uli (ustoz) tasdiqlashi bilan amaliyot soatlaringizga qo'shiladi va OTMga yuboriladi."
    )
    await msg.answer(reply, parse_mode="HTML")
