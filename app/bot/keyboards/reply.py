"""
Reply keyboard layouts for the Telegram bot.

ReplyKeyboardMarkup is used for persistent menu buttons visible
below the message input field.
"""

from aiogram.types import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main bot menu shown after /start command."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📸 Сообщить о граффити"),
                KeyboardButton(text="📋 Мои заявки"),
            ],
            [
                KeyboardButton(text="📍 Карта проблемных мест"),
                KeyboardButton(text="ℹ️ О проекте"),
            ],
            [
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие из меню...",
    )


def request_location_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard with 'Share location' button for geolocation step."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Поделиться местоположением",
                    request_location=True,
                )
            ],
            [
                KeyboardButton(text="✏️ Ввести адрес вручную"),
                KeyboardButton(text="❌ Отменить"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Отправьте геолокацию или введите адрес...",
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Single-button keyboard used during multi-step form."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отменить")]],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    """Removes the reply keyboard after completing or cancelling a form."""
    return ReplyKeyboardRemove()
