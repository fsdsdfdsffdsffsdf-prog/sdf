"""
Inline keyboard layouts for the Telegram bot.

InlineKeyboardMarkup is used for buttons attached to specific messages,
such as report confirmation dialogs and status views.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_report_keyboard() -> InlineKeyboardMarkup:
    """Confirmation dialog shown before submitting a new report."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить и отправить",
                    callback_data="report:confirm",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить заявку",
                    callback_data="report:cancel",
                ),
            ],
        ]
    )


def report_status_keyboard(report_number: str) -> InlineKeyboardMarkup:
    """Inline button to check current status of a submitted report."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Обновить статус",
                    callback_data=f"status:{report_number}",
                ),
            ]
        ]
    )


def my_reports_navigation_keyboard(
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Pagination controls for /my_reports list."""
    buttons = []

    nav_row = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="◀️ Назад",
                callback_data=f"my_reports:page:{current_page - 1}",
            )
        )
    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперёд ▶️",
                callback_data=f"my_reports:page:{current_page + 1}",
            )
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append(
        [
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="nav:main_menu",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=buttons)
