"""
Handler for /my_reports command — shows user's submitted reports with pagination.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.inline import my_reports_navigation_keyboard, report_status_keyboard
from app.bot.keyboards.reply import main_menu_keyboard
from app.database.models.report import Report
from app.database.models.enums import ReportStatus
from app.database.session import async_session_factory
from app.core.logging import logger

router = Router(name="user_reports")

_PAGE_SIZE = 5

_STATUS_LABELS = {
    ReportStatus.NEW: "🆕 Новая",
    ReportStatus.UNDER_REVIEW: "🔍 На рассмотрении",
    ReportStatus.APPROVED: "✅ Подтверждена",
    ReportStatus.IN_PROGRESS: "🔧 В работе",
    ReportStatus.COMPLETED: "✔️ Выполнена",
    ReportStatus.REJECTED: "❌ Отклонена",
    ReportStatus.AI_REVIEW_REQUIRED: "🤖 Ожидает проверки",
}


@router.message(Command("my_reports"))
@router.message(F.text == "📋 Мои заявки")
async def cmd_my_reports(message: Message, db_user) -> None:
    """Shows the first page of the user's reports."""
    if db_user is None:
        await message.answer("⚠️ Не удалось загрузить данные. Попробуйте /start")
        return

    await _show_reports_page(message, db_user.id, page=1)


@router.callback_query(F.data.startswith("my_reports:page:"))
async def paginate_reports(callback: CallbackQuery, db_user) -> None:
    """Handles pagination for the user's reports list."""
    await callback.answer()
    page = int(callback.data.split(":")[-1])
    await _show_reports_page(callback.message, db_user.id, page=page, edit=True)


@router.callback_query(F.data.startswith("status:"))
async def check_report_status(callback: CallbackQuery) -> None:
    """Shows the current status of a specific report."""
    await callback.answer()
    report_number = callback.data.split(":", 1)[1]

    async with async_session_factory() as session:
        result = await session.execute(
            select(Report).where(Report.report_number == report_number)
        )
        report = result.scalar_one_or_none()

    if not report:
        await callback.message.answer(f"⚠️ Заявка {report_number} не найдена.")
        return

    status_label = _STATUS_LABELS.get(report.status, report.status.value)
    await callback.message.answer(
        f"📋 <b>Заявка {report_number}</b>\n\n"
        f"Статус: <b>{status_label}</b>\n"
        f"Дата: {report.created_at.strftime('%d.%m.%Y %H:%M')} UTC",
        parse_mode="HTML",
    )


async def _show_reports_page(
    message: Message,
    user_db_id: int,
    page: int,
    edit: bool = False,
) -> None:
    """Fetches and renders a paginated list of user's reports."""
    async with async_session_factory() as session:
        # Count total reports for the user
        count_result = await session.execute(
            select(func.count()).select_from(Report).where(Report.user_id == user_db_id)
        )
        total = count_result.scalar_one()

        if total == 0:
            text = (
                "📋 <b>Мои заявки</b>\n\n"
                "У вас пока нет зарегистрированных заявок.\n\n"
                "Нажмите «📸 Сообщить о граффити» чтобы создать первую!"
            )
            await message.answer(text, parse_mode="HTML", reply_markup=main_menu_keyboard())
            return

        total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        page = max(1, min(page, total_pages))
        offset = (page - 1) * _PAGE_SIZE

        # Fetch page of reports
        reports_result = await session.execute(
            select(Report)
            .where(Report.user_id == user_db_id)
            .order_by(Report.created_at.desc())
            .offset(offset)
            .limit(_PAGE_SIZE)
        )
        reports = reports_result.scalars().all()

    lines = [f"📋 <b>Мои заявки</b> (стр. {page}/{total_pages}, всего: {total})\n"]
    for r in reports:
        status_label = _STATUS_LABELS.get(r.status, r.status.value)
        date_str = r.created_at.strftime("%d.%m.%Y")
        lines.append(f"• <code>{r.report_number}</code> — {status_label} ({date_str})")

    text = "\n".join(lines)
    keyboard = my_reports_navigation_keyboard(page, total_pages)

    if edit:
        await message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
