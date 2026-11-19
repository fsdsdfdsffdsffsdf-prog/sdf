"""
Report creation handlers — 5-step FSM flow:

  Step 1: User triggers report flow  → waiting_for_photo
  Step 2: User sends photo           → waiting_for_location
  Step 3: User shares location       → waiting_for_description
  Step 4: User writes description    → confirm_submission
  Step 5: User confirms              → Report saved, AI task enqueued
"""

import io
from typing import Optional

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, PhotoSize

from app.bot.keyboards.inline import confirm_report_keyboard
from app.bot.keyboards.reply import (
    cancel_keyboard,
    main_menu_keyboard,
    remove_keyboard,
    request_location_keyboard,
)
from app.bot.states.report_form import ReportForm
from app.config import get_settings
from app.core.logging import logger
from app.database.session import async_session_factory
from app.services.report_service import ReportService
from app.services.storage_service import StorageService

settings = get_settings()
router = Router(name="report")

# ── Step 1: Trigger the report flow ──────────────────────────────────────────

@router.message(Command("new_report"))
@router.message(F.text == "📸 Сообщить о граффити")
async def start_report(message: Message, state: FSMContext) -> None:
    """Initiates the graffiti report creation FSM."""
    await state.clear()
    await state.set_state(ReportForm.waiting_for_photo)
    await message.answer(
        "📸 <b>Шаг 1 из 4 — Фотография</b>\n\n"
        "Пожалуйста, отправьте чёткое фото объекта с граффити.\n\n"
        "📌 <i>Убедитесь, что фото хорошо освещено и граффити видно полностью.</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


# ── Step 2: Receive and validate photo ───────────────────────────────────────

@router.message(ReportForm.waiting_for_photo, F.photo)
async def receive_photo(message: Message, state: FSMContext, bot) -> None:
    """
    Downloads the photo from Telegram CDN, validates it via StorageService,
    and saves it to the local storage directory.
    """
    # Always use the highest-quality photo (last item in array)
    photo: PhotoSize = message.photo[-1]

    status_msg = await message.answer(
        "⏳ Загружаю и проверяю фотографию...",
        reply_markup=remove_keyboard(),
    )

    try:
        # Download from Telegram servers
        file_info = await bot.get_file(photo.file_id)
        file_bytes: io.BytesIO = await bot.download_file(file_info.file_path)

        # Validate and save using StorageService
        storage = StorageService(settings.storage_dir)
        saved_path = await storage.save_photo(file_bytes.read())

        await state.update_data(photo_path=str(saved_path), photo_file_id=photo.file_id)
        await state.set_state(ReportForm.waiting_for_location)

        await status_msg.delete()
        await message.answer(
            "✅ Фото принято!\n\n"
            "📍 <b>Шаг 2 из 4 — Геолокация</b>\n\n"
            "Укажите, где находится объект:\n"
            "• Нажмите кнопку <b>«Поделиться местоположением»</b>\n"
            "• Или введите адрес вручную текстом",
            parse_mode="HTML",
            reply_markup=request_location_keyboard(),
        )
    except ValueError as exc:
        # Validation failure (wrong format, too large, etc.)
        await status_msg.delete()
        await message.answer(
            f"❌ Фото не прошло проверку:\n<code>{exc}</code>\n\n"
            "Пожалуйста, отправьте другое фото.",
            parse_mode="HTML",
            reply_markup=cancel_keyboard(),
        )
    except Exception as exc:
        logger.exception("Photo download/save failed: %s", exc)
        await status_msg.delete()
        await message.answer(
            "⚠️ Не удалось загрузить фото. Попробуйте ещё раз.",
            reply_markup=cancel_keyboard(),
        )


@router.message(ReportForm.waiting_for_photo)
async def photo_wrong_input(message: Message) -> None:
    """Rejects non-photo inputs during the photo step."""
    await message.answer(
        "📸 Пожалуйста, отправьте именно <b>фотографию</b> (не файл, не текст).\n"
        "Или нажмите ❌ Отменить для возврата в меню.",
        parse_mode="HTML",
    )


# ── Step 3: Receive location ──────────────────────────────────────────────────

@router.message(ReportForm.waiting_for_location, F.location)
async def receive_location(message: Message, state: FSMContext) -> None:
    """Stores GPS coordinates from Telegram Location API."""
    lat = message.location.latitude
    lon = message.location.longitude

    await state.update_data(latitude=lat, longitude=lon, address=None)
    await state.set_state(ReportForm.waiting_for_description)

    await message.answer(
        f"✅ Геолокация получена: <code>{lat:.6f}, {lon:.6f}</code>\n\n"
        "✏️ <b>Шаг 3 из 4 — Описание</b>\n\n"
        "Добавьте краткое описание проблемы.\n"
        "Например: <i>«Надпись на стене подъезда, 3-й этаж снаружи»</i>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ReportForm.waiting_for_location, F.text == "✏️ Ввести адрес вручную")
async def request_manual_address(message: Message, state: FSMContext) -> None:
    """Prompts user to type the address as plain text."""
    await state.update_data(address_mode="manual")
    await message.answer(
        "✏️ Введите адрес объекта:\n"
        "Например: <code>ул. Пушкина, д. 10, г. Москва</code>",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


@router.message(ReportForm.waiting_for_location, F.text)
async def receive_manual_address(message: Message, state: FSMContext) -> None:
    """Stores manually entered address text."""
    data = await state.get_data()

    if message.text in ("❌ Отменить", "/cancel"):
        return  # Handled by common cancel handler

    address = message.text.strip()
    if len(address) < 5:
        await message.answer("⚠️ Адрес слишком короткий. Уточните, пожалуйста.")
        return

    await state.update_data(latitude=None, longitude=None, address=address)
    await state.set_state(ReportForm.waiting_for_description)

    await message.answer(
        f"✅ Адрес сохранён: <code>{address}</code>\n\n"
        "✏️ <b>Шаг 3 из 4 — Описание</b>\n\n"
        "Добавьте краткое описание проблемы:",
        parse_mode="HTML",
        reply_markup=cancel_keyboard(),
    )


# ── Step 4: Receive description ───────────────────────────────────────────────

@router.message(ReportForm.waiting_for_description, F.text)
async def receive_description(message: Message, state: FSMContext) -> None:
    """Stores description and shows preview for confirmation."""
    if message.text in ("❌ Отменить", "/cancel"):
        return

    description = message.text.strip()
    if len(description) < 5:
        await message.answer("⚠️ Описание слишком короткое. Добавьте больше деталей.")
        return
    if len(description) > 2000:
        await message.answer("⚠️ Описание слишком длинное. Максимум 2000 символов.")
        return

    await state.update_data(description=description)
    data = await state.get_data()
    await state.set_state(ReportForm.confirm_submission)

    # Build preview text
    location_str = (
        f"📍 GPS: {data['latitude']:.6f}, {data['longitude']:.6f}"
        if data.get("latitude")
        else f"📍 Адрес: {data.get('address', 'не указан')}"
    )

    preview = (
        "📋 <b>Шаг 4 из 4 — Подтверждение</b>\n\n"
        "Проверьте данные вашей заявки:\n\n"
        f"{location_str}\n"
        f"💬 Описание: {description}\n\n"
        "🤖 <i>После отправки AI проанализирует фотографию автоматически.</i>\n\n"
        "Всё верно? Отправить заявку?"
    )

    await message.answer(
        preview,
        parse_mode="HTML",
        reply_markup=confirm_report_keyboard(),
    )


# ── Step 5: Confirm and create report ────────────────────────────────────────

@router.callback_query(ReportForm.confirm_submission, F.data == "report:confirm")
async def confirm_report(callback: CallbackQuery, state: FSMContext, db_user) -> None:
    """Creates the report in the database and enqueues the AI analysis task."""
    await callback.answer()

    if db_user is None:
        await callback.message.answer(
            "⚠️ Не удалось идентифицировать пользователя. Попробуйте /start"
        )
        await state.clear()
        return

    data = await state.get_data()
    await state.clear()

    processing_msg = await callback.message.answer(
        "⏳ Создаю заявку и запускаю AI-анализ...",
        reply_markup=remove_keyboard(),
    )

    try:
        async with async_session_factory() as session:
            service = ReportService(session)
            report = await service.create_report(
                user_id=db_user.id,
                photo_path=data["photo_path"],
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                address=data.get("address"),
                description=data.get("description"),
            )
            await session.commit()

        await processing_msg.delete()
        await callback.message.answer(
            f"✅ <b>Заявка успешно зарегистрирована!</b>\n\n"
            f"🔖 Номер: <code>{report.report_number}</code>\n"
            f"📊 Статус: <b>Новая</b>\n\n"
            f"🤖 AI-анализ выполняется в фоновом режиме.\n"
            f"Вы получите уведомление с результатами.\n\n"
            f"Спасибо за помощь в поддержании чистоты города! 🌿",
            parse_mode="HTML",
            reply_markup=main_menu_keyboard(),
        )

        logger.info(
            "Report %s created by user tg_id=%d",
            report.report_number,
            db_user.telegram_id,
        )

    except Exception as exc:
        logger.exception("Failed to create report: %s", exc)
        await processing_msg.delete()
        await callback.message.answer(
            "❌ Произошла ошибка при создании заявки. Попробуйте позже.",
            reply_markup=main_menu_keyboard(),
        )


@router.callback_query(ReportForm.confirm_submission, F.data == "report:cancel")
async def cancel_report_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancels the report submission from the confirmation dialog."""
    await callback.answer("Заявка отменена.")
    await state.clear()
    await callback.message.answer(
        "❌ Заявка отменена. Возвращаю вас в главное меню.",
        reply_markup=main_menu_keyboard(),
    )
