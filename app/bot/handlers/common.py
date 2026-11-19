"""
Common command handlers: /start, /help, /about, /cancel and main menu buttons.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.reply import main_menu_keyboard, remove_keyboard
from app.config import get_settings

settings = get_settings()
router = Router(name="common")

_ABOUT_TEXT = """
🏙️ <b>AntiGraffiti AI</b>

Платформа для обнаружения и регистрации граффити в городской среде.

<b>Как это работает:</b>
1. Вы отправляете фото объекта с граффити
2. AI анализирует изображение автоматически
3. Система создаёт заявку и уведомляет ответственных
4. Вы получаете обновления по статусу вашей заявки

<b>Технологии:</b> Python · FastAPI · aiogram 3 · OpenAI Vision · PostgreSQL

Вместе сделаем город чище! 🌿
"""

_HELP_TEXT = """
❓ <b>Помощь</b>

<b>Команды бота:</b>
/start — Запустить бота и открыть меню
/new_report — Создать новую заявку о граффити
/my_reports — Посмотреть мои заявки
/help — Показать эту справку
/about — О проекте
/cancel — Отменить текущее действие

<b>Как создать заявку:</b>
1. Нажмите «📸 Сообщить о граффити»
2. Отправьте фотографию объекта
3. Поделитесь геолокацией или введите адрес
4. Добавьте краткое описание
5. Подтвердите отправку заявки

<b>Нужна помощь?</b>
Обратитесь в службу поддержки города.
"""


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Handles the /start command. Clears any active FSM state and shows main menu."""
    await state.clear()
    await message.answer(
        f"👋 Добро пожаловать в <b>AntiGraffiti AI</b>, {message.from_user.first_name}!\n\n"
        "Помогите сделать наш город чище.\n"
        "Отправьте фотографию граффити — мы зарегистрируем проблему и передадим в соответствующую службу.\n\n"
        "Выберите действие из меню ниже:",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: Message) -> None:
    """Handles /help command and Help menu button."""
    await message.answer(_HELP_TEXT, parse_mode="HTML")


@router.message(Command("about"))
@router.message(F.text == "ℹ️ О проекте")
async def cmd_about(message: Message) -> None:
    """Handles /about command and About menu button."""
    await message.answer(_ABOUT_TEXT, parse_mode="HTML")


@router.message(Command("cancel"))
@router.message(F.text == "❌ Отменить")
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """
    Handles /cancel command and Cancel button.
    Clears FSM state and returns user to main menu.
    """
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(
            "✅ Нет активных действий для отмены.\n\nВыберите действие из меню:",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        "❌ Действие отменено. Возвращаю вас в главное меню.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "📍 Карта проблемных мест")
async def menu_map(message: Message) -> None:
    """Links user to the public admin map page."""
    settings = get_settings()
    map_url = f"{settings.WEBHOOK_URL}/admin/map"
    await message.answer(
        f"🗺️ <b>Карта проблемных мест</b>\n\n"
        f"Просмотрите все зарегистрированные случаи граффити на карте:\n"
        f"👉 <a href='{map_url}'>{map_url}</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
