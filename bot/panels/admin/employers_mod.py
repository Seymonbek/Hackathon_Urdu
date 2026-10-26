from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.core.callbacks import AdminVerifyAction
from bot.core.i18n import get_button_variants
from bot.db.repositories.users_repo import UsersRepo
from bot.db.repositories.employers_repo import EmployersRepo

router = Router()


@router.message(F.text.in_(get_button_variants("BTN_ADM_VERIFY")))
async def list_unverified_employers(msg: Message):
    lang = await UsersRepo.get_user_lang(msg.from_user.id)
    unverified = await EmployersRepo.get_all_unverified()
    if not unverified:
        empty_txt = "✅ Barcha tashkilotlar tekshirilgan va tasdiqlangan. Yangi kutilayotgan tashkilot yo'q." if lang == "uz" else ("✅ Все организации проверены и верифицированы." if lang == "ru" else "✅ All organizations verified.")
        await msg.answer(empty_txt)
        return

    for emp in unverified[:5]:
        org_type_label = "🏛 Davlat Organi / Shifoxona / Sud" if emp.get("org_type") == "state_agency" else "🏢 Tijoriy Korxona"
        text = (
            f"🏢 **Tashkilot tekshiruvi:**\n\n"
            f"• Nomi: **{emp.get('company_name')}** ({org_type_label})\n"
            f"• Soha: {emp.get('category')}\n"
            f"• Manzil: {emp.get('address')}\n"
            f"• Telefon: {emp.get('contact_phone')}\n"
            f"• Mas'ul: {emp.get('contact_person')}\n"
        )

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ Tasdiqlash (✔️)",
                        callback_data=AdminVerifyAction(target="employer", action="approve", id=emp["id"]).pack(),
                    ),
                    InlineKeyboardButton(
                        text="🚫 Rad etish",
                        callback_data=AdminVerifyAction(target="employer", action="reject", id=emp["id"]).pack(),
                    ),
                ]
            ]
        )
        await msg.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(AdminVerifyAction.filter(F.action == "approve"))
async def process_approve_employer(call: CallbackQuery, callback_data: AdminVerifyAction):
    await EmployersRepo.verify_employer(callback_data.id, True)
    await call.answer("Tashkilot tasdiqlandi!", show_alert=True)
    await call.message.edit_text("✅ **Tashkilot tekshirildi va tasdiqlandi! (✔️ Rasmiy belgi berildi)**")


@router.callback_query(AdminVerifyAction.filter(F.action == "reject"))
async def process_reject_employer(call: CallbackQuery, callback_data: AdminVerifyAction):
    await EmployersRepo.verify_employer(callback_data.id, False)
    await call.answer("Rad etildi.", show_alert=True)
    await call.message.edit_text("❌ Tashkilot tasdiqlanmadi.")
