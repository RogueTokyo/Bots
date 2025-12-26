import logging
import json
import os
from typing import Dict, List, Optional, Any, Tuple, Union
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, Document, InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

logger = logging.getLogger(__name__)

from bot.utils.database import SessionLocal
from bot.utils.crud import (
    create_shop, get_shop_by_id, get_shops_by_user_id, get_active_shops_by_user_id,
    update_shop, delete_shop, ShopCreate, ShopUpdate
)
from bot.utils.states import ShopStates
from bot.utils.keyboards import (
    get_main_menu_keyboard, get_confirmation_keyboard,
    get_shops_keyboard, get_shop_actions_keyboard, get_products_count_keyboard
)
from bot.services.api_client import api_client, create_sample_products

# Создаем роутер для обработчиков
router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start"""
    try:
        user_id: int = message.from_user.id
        username: str = message.from_user.username or "пользователь"

        logger.info(f"Пользователь {user_id} ({username}) запустил бота")

        welcome_text = (
            " <b>Здравствуйте!</b>\n\n"
            "Я помогу вам управлять вашими магазинами.\n\n"
            "Доступные команды:\n"
            "• /add_shop - добавить новый магазин\n"
            "• /shops - просмотреть ваши магазины\n"
            "• /upload_excel - загрузить данные из Excel\n\n"
            "Выберите действие:"
        )

        await message.answer(
            welcome_text,
            reply_markup=get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка в команде /start для пользователя {message.from_user.id}: {e}")
        await message.answer(
            " <b>Произошла ошибка при запуске бота</b>\n\n"
            "Пожалуйста, попробуйте еще раз или обратитесь к администратору.",
            reply_markup=get_main_menu_keyboard()
        )

@router.callback_query(F.data == "add_shop")
async def callback_add_shop(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления магазина"""
    try:
        user_id = callback.from_user.id
        logger.info(f"Пользователь {user_id} начал добавление магазина")

        await callback.message.edit_text(
            " <b>Добавление нового магазина</b>\n\n"
            "Введите название магазина:"
        )

        await state.set_state(ShopStates.waiting_for_shop_name)
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при начале добавления магазина для пользователя {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            " <b>Произошла ошибка</b>\n\n"
            "Не удалось начать процесс добавления магазина.\n"
            "Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )
        await callback.answer()

@router.message(ShopStates.waiting_for_shop_name)
async def process_shop_name(message: Message, state: FSMContext):
    """Обработка ввода названия магазина"""
    try:
        if not message.text:
            await message.answer(
                " Пожалуйста, введите название магазина (не пустое сообщение).\n"
                "Введите название магазина:"
            )
            return

        shop_name = message.text.strip()

        if len(shop_name) < 2:
            await message.answer(
                " Название магазина должно содержать минимум 2 символа.\n"
                "Введите название магазина:"
            )
            return

        if len(shop_name) > 255:
            await message.answer(
                " Название магазина слишком длинное (максимум 255 символов).\n"
                "Введите название магазина:"
            )
            return

        # Проверяем на недопустимые символы
        if any(char in shop_name for char in ['<', '>', '&', '"', "'"]):
            await message.answer(
                " Название магазина содержит недопустимые символы.\n"
                "Используйте только буквы, цифры и пробелы.\n"
                "Введите название магазина:"
            )
            return

        await state.update_data(shop_name=shop_name)
        logger.info(f"Пользователь {message.from_user.id} ввел название магазина: {shop_name}")

        await message.answer(
            f" Название: <b>{shop_name}</b>\n\n"
            "Теперь введите Client ID:"
        )
        await state.set_state(ShopStates.waiting_for_client_id)

    except Exception as e:
        logger.error(f"Ошибка при обработке названия магазина для пользователя {message.from_user.id}: {e}")
        await message.answer(
            " <b>Произошла ошибка при обработке названия</b>\n\n"
            "Попробуйте ввести название магазина еще раз:"
        )

@router.message(ShopStates.waiting_for_client_id)
async def process_client_id(message: Message, state: FSMContext):
    """Обработка ввода Client ID"""
    try:
        if not message.text:
            await message.answer(
                " Пожалуйста, введите Client ID (не пустое сообщение).\n"
                "Введите Client ID:"
            )
            return

        client_id = message.text.strip()

        if not client_id:
            await message.answer(
                " Client ID не может быть пустым.\n"
                "Введите Client ID:"
            )
            return

        if len(client_id) > 255:
            await message.answer(
                " Client ID слишком длинный (максимум 255 символов).\n"
                "Введите Client ID:"
            )
            return

        # Проверяем на допустимые символы для ID
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', client_id):
            await message.answer(
                " Client ID может содержать только буквы, цифры, дефисы и подчеркивания.\n"
                "Введите Client ID:"
            )
            return

        await state.update_data(client_id=client_id)
        logger.info(f"Пользователь {message.from_user.id} ввел Client ID: {client_id}")

        await message.answer(
            f" Client ID: <b>{client_id}</b>\n\n"
            "Теперь введите API Key:"
        )
        await state.set_state(ShopStates.waiting_for_api_key)

    except Exception as e:
        logger.error(f"Ошибка при обработке Client ID для пользователя {message.from_user.id}: {e}")
        await message.answer(
            " <b>Произошла ошибка при обработке Client ID</b>\n\n"
            "Попробуйте ввести Client ID еще раз:"
        )

@router.message(ShopStates.waiting_for_api_key)
async def process_api_key(message: Message, state: FSMContext):
    """Обработка ввода API Key"""
    try:
        if not message.text:
            await message.answer(
                " Пожалуйста, введите API Key (не пустое сообщение).\n"
                "Введите API Key:"
            )
            return

        api_key = message.text.strip()

        if not api_key:
            await message.answer(
                " API Key не может быть пустым.\n"
                "Введите API Key:"
            )
            return

        if len(api_key) > 500:
            await message.answer(
                " API Key слишком длинный (максимум 500 символов).\n"
                "Введите API Key:"
            )
            return

        # Проверяем минимальную длину
        if len(api_key) < 10:
            await message.answer(
                " API Key слишком короткий (минимум 10 символов).\n"
                "Введите API Key:"
            )
            return

        # Сохраняем данные и переходим к подтверждению
        await state.update_data(api_key=api_key)

        # Получаем все данные для подтверждения
        data = await state.get_data()

        confirmation_text = (
            " <b>Подтверждение создания магазина</b>\n\n"
            f" Название: <b>{data['shop_name']}</b>\n"
            f"Client ID: <b>{data['client_id']}</b>\n"
            f" API Key: <b>{api_key[:20]}...</b>\n\n"
            "Все данные верны?"
        )

        logger.info(f"Пользователь {message.from_user.id} завершил ввод данных для магазина: {data['shop_name']}")

        await message.answer(
            confirmation_text,
            reply_markup=get_confirmation_keyboard()
        )
        await state.set_state(ShopStates.confirming_shop_creation)

    except Exception as e:
        logger.error(f"Ошибка при обработке API Key для пользователя {message.from_user.id}: {e}")
        await message.answer(
            " <b>Произошла ошибка при обработке API Key</b>\n\n"
            "Попробуйте ввести API Key еще раз:"
        )

@router.callback_query(F.data == "confirm_yes", ShopStates.confirming_shop_creation)
async def confirm_shop_creation(callback: CallbackQuery, state: FSMContext):
    """Подтверждение создания магазина"""
    data = await state.get_data()

    try:
        # Создаем магазин в базе данных
        shop_data = ShopCreate(
            user_id=callback.from_user.id,
            name=data['shop_name'],
            client_id=data['client_id'],
            api_key=data['api_key'],
            is_active=True
        )

        db = SessionLocal()
        new_shop = create_shop(db, shop_data)
        db.close()

        logger.info(f"Магазин '{new_shop.name}' успешно создан для пользователя {callback.from_user.id}")

        await callback.message.edit_text(
            f" <b>Магазин успешно создан!</b>\n\n"
            f" Название: <b>{new_shop.name}</b>\n"
            f"ID: <b>{new_shop.id}</b>\n\n"
            "Выберите следующее действие:",
            reply_markup=get_main_menu_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при создании магазина для пользователя {callback.from_user.id}: {e}")
        logger.error(f"Данные магазина: {data}")

        # Определяем тип ошибки для более понятного сообщения
        error_message = " Произошла ошибка при создании магазина.\n"
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            error_message += "Магазин с таким Client ID уже существует.\n"
            error_message += "Используйте другой Client ID."
        elif "connection" in str(e).lower():
            error_message += "Проблема с подключением к базе данных.\n"
            error_message += "Попробуйте позже."
        else:
            error_message += "Попробуйте еще раз или обратитесь к администратору."

        await callback.message.edit_text(
            error_message,
            reply_markup=get_main_menu_keyboard()
        )

    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "confirm_no", ShopStates.confirming_shop_creation)
async def cancel_shop_creation(callback: CallbackQuery, state: FSMContext):
    """Отмена создания магазина"""
    await callback.message.edit_text(
        " Создание магазина отменено.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "shops")
@router.message(Command("shops"))
async def cmd_shops(callback_or_message, state: FSMContext, page: int = 0):
    """Показать список магазинов пользователя"""
    # Определяем, от кого пришел запрос
    if isinstance(callback_or_message, CallbackQuery):
        user_id = callback_or_message.from_user.id
        message = callback_or_message.message
        await callback_or_message.answer()
    else:
        user_id = callback_or_message.from_user.id
        message = callback_or_message

    try:
        db = SessionLocal()
        shops = get_shops_by_user_id(db, user_id)
        db.close()

        if not shops:
            await message.edit_text(
                " <b>У вас пока нет магазинов</b>\n\n"
                "Добавьте первый магазин:",
                reply_markup=get_main_menu_keyboard()
            )
            return

        # Показываем список магазинов с пагинацией
        keyboard = get_shops_keyboard(shops, page)
        total_shops = len(shops)

        text = (
            f" <b>Ваши магазины</b> ({total_shops})\n\n"
            "Выберите магазин для управления:"
        )

        if isinstance(callback_or_message, CallbackQuery):
            await message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при получении магазинов: {e}")
        error_text = " Произошла ошибка при загрузке магазинов."
        if isinstance(callback_or_message, CallbackQuery):
            await message.edit_text(error_text, reply_markup=get_main_menu_keyboard())
        else:
            await message.answer(error_text, reply_markup=get_main_menu_keyboard())

@router.callback_query(F.data.startswith("shop_"))
async def select_shop(callback: CallbackQuery, state: FSMContext):
    """Выбор конкретного магазина"""
    shop_id = int(callback.data.split("_")[1])

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)
        db.close()

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        status_emoji = "" if shop.is_active else ""
        shop_info = (
            f" <b>{shop.name}</b>\n\n"
            f" Статус: {status_emoji} {'Активен' if shop.is_active else 'Неактивен'}\n"
            f"Client ID: <code>{shop.client_id}</code>\n"
            f" API Key: <code>{shop.api_key[:20]}...</code>\n\n"
            "Выберите действие:"
        )

        await callback.message.edit_text(
            shop_info,
            reply_markup=get_shop_actions_keyboard(shop_id)
        )

    except Exception as e:
        logger.error(f"Ошибка при получении магазина: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при загрузке магазина.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("toggle_"))
async def toggle_shop_status(callback: CallbackQuery):
    """Переключение статуса магазина"""
    shop_id = int(callback.data.split("_")[1])

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            db.close()
            await callback.answer()
            return

        # Переключаем статус
        new_status = not shop.is_active
        update_data = ShopUpdate(is_active=new_status)
        updated_shop = update_shop(db, shop_id, update_data)
        db.close()

        if updated_shop:
            status_emoji = "" if updated_shop.is_active else ""
            status_text = "активен" if updated_shop.is_active else "неактивен"

            await callback.message.edit_text(
                f" Статус магазина <b>{updated_shop.name}</b> изменен на: {status_emoji} {status_text}",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                " Не удалось изменить статус магазина.",
                reply_markup=get_main_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при изменении статуса магазина: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при изменении статуса.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("delete_"))
async def delete_shop_callback(callback: CallbackQuery):
    """Удаление магазина"""
    shop_id = int(callback.data.split("_")[1])

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            db.close()
            await callback.answer()
            return

        # Удаляем магазин
        deleted = delete_shop(db, shop_id)
        db.close()

        if deleted:
            await callback.message.edit_text(
                f" Магазин <b>{shop.name}</b> успешно удален.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                " Не удалось удалить магазин.",
                reply_markup=get_main_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при удалении магазина: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при удалении магазина.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data == "upload_excel")
async def callback_upload_excel(callback: CallbackQuery):
    """Обработчик загрузки Excel файла"""
    await callback.message.edit_text(
        "<b>Загрузка товаров из Excel</b>\n\n"
        "Отправьте Excel файл (.xlsx или .xls) с данными товаров для отправки на API.\n\n"
        "<b>Структура файла:</b>\n"
        "• <b>Столбец 1:</b> <code>Название товара</code> - название товара\n"
        "• <b>Столбец 2:</b> <code>Количество товара</code> - количество единиц\n\n"
        " <b>Пример:</b>\n"
        "<code>Название товара | Количество товара</code>\n"
        "<code>Футболка        | 10</code>\n"
        "<code>Джинсы         | 13</code>\n"
        "<code>Кроссовки      | 5</code>\n\n"
        "<b>Требования:</b>\n"
        "• Первая строка - заголовки колонок\n"
        "• Названия товаров не должны быть пустыми\n"
        "• Количество - целые положительные числа\n"
        "• Максимум 10 MB\n\n",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Отмена", callback_data="main_menu")
        ]])
    )
    await callback.answer()

@router.message(F.document)
async def handle_document(message: Message):
    """Обработка загруженного документа"""
    try:
        document = message.document

        if not document:
            await message.answer(" Документ не найден в сообщении.")
            return

        if not document.file_name:
            await message.answer(" У файла отсутствует имя.")
            return

        # Проверяем размер файла (максимум 10MB)
        if document.file_size and document.file_size > 10 * 1024 * 1024:
            await message.answer(
                " Файл слишком большой (максимум 10MB).\n"
                "Пожалуйста, загрузите файл меньшего размера."
            )
            return

        # Проверяем, что это Excel файл
        if not document.file_name.lower().endswith(('.xlsx', '.xls')):
            await message.answer(
                " Пожалуйста, отправьте файл в формате Excel (.xlsx или .xls)\n"
                f"Получен файл: <code>{document.file_name}</code>"
            )
            return

        logger.info(f"Пользователь {message.from_user.id} загрузил файл: {document.file_name} ({document.file_size} bytes)")

        # Создаем уникальное имя файла
        import uuid
        file_extension = document.file_name.split('.')[-1]
        unique_filename = f"upload_{message.from_user.id}_{uuid.uuid4()}.{file_extension}"
        file_path = f"/tmp/{unique_filename}"

        try:
            # Скачиваем файл
            await message.bot.download(document, file_path)

            # Проверяем, что файл действительно скачался
            if not os.path.exists(file_path):
                raise FileNotFoundError("Файл не был сохранен")

            file_size = os.path.getsize(file_path)
            logger.info(f"Файл успешно скачан: {file_path} ({file_size} bytes)")

            # Обрабатываем Excel файл
            await process_excel_file(message, file_path)

        except Exception as download_error:
            logger.error(f"Ошибка при скачивании файла {document.file_name}: {download_error}")
            await message.answer(
                " <b>Ошибка при загрузке файла</b>\n\n"
                "Не удалось скачать файл с серверов Telegram.\n"
                "Попробуйте загрузить файл еще раз."
            )
        finally:
            # Очищаем временный файл
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Временный файл удален: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Не удалось удалить временный файл {file_path}: {cleanup_error}")

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке документа от пользователя {message.from_user.id}: {e}")
        await message.answer(
            " <b>Критическая ошибка при обработке файла</b>\n\n"
            "Произошла непредвиденная ошибка.\n"
            "Обратитесь к администратору или попробуйте позже."
        )

async def process_excel_file(message: Message, file_path: str) -> None:
    """Обработка Excel файла с товарами и отправка на API"""
    try:
        import pandas as pd
        import json
        import os

        # Читаем Excel файл с помощью pandas
        # header=0 - первая строка содержит названия колонок
        # sheet_name=0 - читаем первый лист
        df = pd.read_excel(file_path, engine='openpyxl', header=0, sheet_name=0)
        
        # Очищаем названия колонок от лишних пробелов
        df.columns = df.columns.str.strip()

        # Проверяем наличие необходимых колонок для товаров
        expected_headers = ['Название товара', 'Количество товара']
        missing_headers = [header for header in expected_headers if header not in df.columns]

        if missing_headers:
            available_columns = ', '.join(df.columns.tolist())
            await message.answer(
                f" <b>Неверный формат файла</b>\n\n"
                f"Отсутствуют обязательные колонки: {', '.join(missing_headers)}\n\n"
                f"Файл должен содержать следующие колонки:\n"
                f"• <code>Название товара</code> - название товара из каталога\n"
                f"• <code>Количество товара</code> - количество единиц товара\n\n"
                f" <b>Найденные колонки в вашем файле:</b>\n"
                f"<code>{available_columns}</code>\n\n"
                f"Пожалуйста, переименуйте колонки в Excel файле и загрузите его снова."
            )
            return

        if len(df) == 0:
            await message.answer(
                " <b>Excel файл пустой</b>\n\n"
                "Файл не содержит данных о товарах.\n"
                "Пожалуйста, добавьте данные в Excel файл и загрузите его снова."
            )
            return

        # Очищаем данные от NaN значений и пустых строк
        df = df.fillna('')
        # Удаляем строки, где обе колонки пустые
        df = df[(df['Название товара'].astype(str).str.strip() != '') | (df['Количество товара'].astype(str).str.strip() != '')]
        
        # Проверяем, остались ли данные после очистки
        if len(df) == 0:
            await message.answer(
                " <b>No valid data found</b>\n\n"
                "После удаления пустых строк данных не осталось.\n"
                "Пожалуйста, убедитесь, что Excel файл содержит корректные данные."
            )
            return

        # Получаем активный магазин пользователя
        db = SessionLocal()
        try:
            active_shops = get_active_shops_by_user_id(db, message.from_user.id)
            if not active_shops:
                await message.answer(
                    " <b>Нет активного магазина</b>\n\n"
                    "У вас нет активных магазинов. Сначала добавьте магазин командой /add_shop\n"
                    "или активируйте существующий через /shops"
                )
                return

            # Если есть только один активный магазин, используем его
            if len(active_shops) == 1:
                active_shop = active_shops[0]
            else:
                # Если несколько активных, берем первый (пользователь должен выбрать через /shops)
                active_shop = active_shops[0]
                await message.answer(
                    f"<b>Выбран активный магазин:</b> {active_shop.name}\n"
                    f"Если хотите использовать другой магазин, выберите его через /shops"
                )

        except Exception as e:
            logger.error(f"Ошибка при получении активного магазина: {e}")
            await message.answer(" Ошибка при работе с базой данных")
            return
        finally:
            db.close()

        # Обрабатываем товары
        products: Dict[str, int] = {}
        success_count: int = 0
        error_count: int = 0
        validation_errors: List[str] = []

        for excel_row_num, (idx, row) in enumerate(df.iterrows(), start=2):  # Нумерация с 2 (после заголовка)
            try:
                # Извлекаем и очищаем данные
                product_name = str(row['Название товара']).strip()
                quantity_str = str(row['Количество товара']).strip()

                # Валидация данных
                if not product_name:
                    error_count += 1
                    validation_errors.append(f"Строка {excel_row_num}: пустое название товара")
                    continue

                if not quantity_str:
                    error_count += 1
                    validation_errors.append(f"Строка {excel_row_num}: пустое количество товара")
                    continue

                try:
                    quantity = int(float(quantity_str))  # Преобразуем в число
                    if quantity <= 0:
                        raise ValueError("Количество должно быть положительным")
                except (ValueError, TypeError):
                    error_count += 1
                    validation_errors.append(f"Строка {excel_row_num}: некорректное количество '{quantity_str}'")
                    continue

                # Добавляем товар в словарь
                products[product_name] = quantity
                success_count += 1

            except Exception as e:
                logger.error(f"Ошибка в строке {excel_row_num}: {e}")
                error_count += 1
                validation_errors.append(f"Строка {excel_row_num}: {str(e)}")
                continue

        # Если нет успешных товаров, завершаем обработку
        if success_count == 0:
            error_summary = " <b>Ошибки валидации:</b>\n"
            for error in validation_errors[:5]:
                error_summary += f"• {error}\n"
            if len(validation_errors) > 5:
                error_summary += f"• ... и еще {len(validation_errors) - 5} ошибок\n"
            
            await message.answer(
                f" <b>Ошибка обработки файла</b>\n\n"
                f" Файл: <code>{os.path.basename(file_path)}</code>\n"
                f" Всего строк: <b>{len(df)}</b>\n"
                f" Успешно обработано: <b>{success_count}</b>\n"
                f" Ошибок: <b>{error_count}</b>\n\n"
                f"{error_summary}\n"
                f"<b>Пожалуйста, проверьте:</b>\n"
                f"• Колонка 'Название товара' содержит названия\n"
                f"• Колонка 'Количество товара' содержит числовые значения\n"
                f"• Нет пустых строк\n\n"
                f"Загрузите исправленный файл."
            )
            return

        # Отправляем результат обработки пользователю
        result_text = (
            f" <b>Обработка Excel файла завершена</b>\n\n"
            f" Файл: <code>{os.path.basename(file_path)}</code>\n"
            f" Всего строк: <b>{len(df)}</b>\n"
            f" Успешно обработано: <b>{success_count}</b>\n"
            f" Ошибок: <b>{error_count}</b>\n\n"
            f" <b>Найдено товаров:</b> {len(products)}\n"
            f" <b>Магазин:</b> {active_shop.name} (ID: {active_shop.client_id})"
        )

        if validation_errors:
            result_text += "\n\n <b>Ошибки валидации:</b>\n"
            for error in validation_errors[:3]:  # Показываем первые 3 ошибки
                result_text += f"• {error}\n"
            if len(validation_errors) > 3:
                result_text += f"• ... и еще {len(validation_errors) - 3} ошибок\n"

        # Создаем клавиатуру для отправки товаров
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Отправить на API", callback_data=f"send_products_{active_shop.id}"),
                InlineKeyboardButton(text=" Показать товары", callback_data=f"show_products_{active_shop.id}")
            ],
            [
                InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
            ]
        ])

        # Сохраняем товары во временное хранилище для отправки
        products_data = {
            "client_id": active_shop.client_id,
            "api_key": active_shop.api_key,
            "products": products,
            "file_info": {
                "filename": os.path.basename(file_path),
                "total_products": len(products),
                "processed_at": pd.Timestamp.now().isoformat()
            }
        }

        # Сохраняем данные в сессии пользователя (FSM)
        temp_filename = f"products_{message.from_user.id}_{active_shop.id}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json"
        temp_filepath = f"/tmp/{temp_filename}"

        with open(temp_filepath, 'w', encoding='utf-8') as f:
            json.dump(products_data, f, ensure_ascii=False, indent=2)

        # Сохраняем путь к файлу в сообщении для callback'ов
        result_text += f"\n\n Файл сохранен: <code>{temp_filename}</code>"

        await message.answer(result_text, reply_markup=keyboard)

        # Сохраняем путь к JSON файлу в временном хранилище (можно использовать FSM state)
        # Для простоты сохраним в глобальную переменную или файл

    except pd.errors.EmptyDataError:
        await message.answer(
            " Файл Excel пустой или не содержит данных.",
            reply_markup=get_main_menu_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке Excel файла: {e}")
        await message.answer(
            " Произошла ошибка при обработке Excel файла.\n"
            "Проверьте формат файла и данные.",
            reply_markup=get_main_menu_keyboard()
        )

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.edit_text(
        " <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_shops")
async def callback_back_to_shops(callback: CallbackQuery):
    """Возврат к списку магазинов"""
    await cmd_shops(callback)
    await callback.answer()

@router.callback_query(F.data.startswith("page_"))
async def callback_pagination(callback: CallbackQuery):
    """Обработка пагинации"""
    page = int(callback.data.split("_")[1])
    await cmd_shops(callback, page=page)
    await callback.answer()

@router.callback_query(F.data.startswith("send_json_"))
async def callback_send_json(callback: CallbackQuery):
    """Отправка JSON файла пользователю"""
    json_filename = callback.data.replace("send_json_", "")
    json_filepath = f"/tmp/{json_filename}"

    try:
        if not os.path.exists(json_filepath):
            await callback.message.edit_text(
                " JSON файл не найден или был удален.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Отправляем JSON файл
        json_file = FSInputFile(json_filepath)
        await callback.message.answer_document(
            json_file,
            caption=" JSON файл с обработанными данными магазинов"
        )

        # Возвращаемся в главное меню
        await callback.message.answer(
            "Файл отправлен! Выберите следующее действие:",
            reply_markup=get_main_menu_keyboard()
        )

        # Удаляем временный файл
        os.remove(json_filepath)

    except Exception as e:
        logger.error(f"Ошибка при отправке JSON файла: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при отправке JSON файла.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("show_json_"))
async def callback_show_json(callback: CallbackQuery):
    """Показ содержимого JSON файла"""
    json_filename = callback.data.replace("show_json_", "")
    json_filepath = f"/tmp/{json_filename}"

    try:
        if not os.path.exists(json_filepath):
            await callback.message.edit_text(
                " JSON файл не найден или был удален.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Читаем и показываем содержимое JSON
        with open(json_filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        # Формируем текстовое представление
        total_shops = len(json_data.get("shops", []))
        file_info = json_data.get("file_info", {})

        json_preview = (
            f" <b>JSON файл: {file_info.get('filename', 'unknown')}</b>\n\n"
            f" Статистика:\n"
            f"• Всего магазинов: <b>{total_shops}</b>\n"
            f"• Обработано: <b>{file_info.get('processed_at', 'unknown')}</b>\n\n"
        )

        # Показываем первые несколько магазинов
        shops = json_data.get("shops", [])[:3]  # Первые 3 для превью
        if shops:
            json_preview += " <b>Примеры данных:</b>\n"
            for i, shop in enumerate(shops, 1):
                json_preview += (
                    f"\n{i}. <b>{shop['name']}</b>\n"
                    f"   ID: <code>{shop['client_id']}</code>\n"
                    f"   API: <code>{shop['api_key'][:20]}...</code>\n"
                )

            if total_shops > 3:
                json_preview += f"\n... и еще <b>{total_shops - 3}</b> магазинов\n"

        # Кнопки действий
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Отправить файл", callback_data=f"send_json_{json_filename}"),
                InlineKeyboardButton(text=" Удалить", callback_data=f"delete_json_{json_filename}")
            ],
            [
                InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
            ]
        ])

        await callback.message.edit_text(
            json_preview,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка при показе JSON файла: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при чтении JSON файла.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("delete_json_"))
async def callback_delete_json(callback: CallbackQuery):
    """Удаление JSON файла"""
    json_filename = callback.data.replace("delete_json_", "")
    json_filepath = f"/tmp/{json_filename}"

    try:
        if os.path.exists(json_filepath):
            os.remove(json_filepath)
            await callback.message.edit_text(
                " JSON файл успешно удален.",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await callback.message.edit_text(
                " JSON файл уже был удален.",
                reply_markup=get_main_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при удалении JSON файла: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при удалении JSON файла.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data == "send_to_api")
async def callback_send_to_api(callback: CallbackQuery):
    """Начало процесса отправки данных на API"""
    user_id = callback.from_user.id

    try:
        db = SessionLocal()
        shops = get_shops_by_user_id(db, user_id)
        db.close()

        # Оптимизированный запрос - получаем только активные магазины
        active_shops = get_active_shops_by_user_id(db, user_id)

        if not active_shops:
            await callback.message.edit_text(
                " <b>Нет активных магазинов</b>\n\n"
                "Для отправки данных на API необходимо иметь хотя бы один активный магазин.\n"
                "Добавьте магазин или активируйте существующий.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Показываем список активных магазинов для выбора
        keyboard = get_shops_keyboard(active_shops, 0, 5)
        await callback.message.edit_text(
            " <b>Отправка данных на API</b>\n\n"
            "Выберите магазин, в который хотите отправить данные:",
            reply_markup=keyboard
        )

    except Exception as e:
        logger.error(f"Ошибка при получении магазинов для отправки: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при загрузке магазинов.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("send_products_"))
async def callback_send_products(callback: CallbackQuery):
    """Выбор количества продуктов для отправки"""
    shop_id = int(callback.data.replace("send_products_", ""))

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)
        db.close()

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        if not shop.is_active:
            await callback.message.edit_text(
                " Магазин неактивен. Активируйте магазин перед отправкой данных.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        shop_info = (
            f" <b>{shop.name}</b>\n\n"
            f" <b>Отправка данных на API</b>\n\n"
            f"Выберите количество тестовых продуктов для отправки:"
        )

        await callback.message.edit_text(
            shop_info,
            reply_markup=get_products_count_keyboard(shop_id)
        )

    except Exception as e:
        logger.error(f"Ошибка при подготовке отправки продуктов: {e}")
        await callback.message.edit_text(
            " Произошла ошибка при подготовке отправки.",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("send_count_"))
async def callback_send_count(callback: CallbackQuery):
    """Отправка выбранного количества продуктов"""
    parts = callback.data.replace("send_count_", "").split("_")
    shop_id = int(parts[0])
    count = int(parts[1])

    await callback.message.edit_text(
        f" Отправка {count} тестовых продуктов...\n"
        "Пожалуйста, подождите."
    )

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)
        db.close()

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Создаем тестовые продукты
        products = create_sample_products(count)

        # Отправляем на API
        response = await api_client.send_products(shop.client_id, shop.api_key, products)

        if response.success:
            success_message = (
                f" <b>Успешная отправка!</b>\n\n"
                f" <b>{shop.name}</b>\n"
                f" Отправлено продуктов: <b>{count}</b>\n"
                f" Статус: <b>HTTP {response.status_code}</b>\n\n"
            )

            if response.data:
                success_message += f" Ответ сервера:\n<code>{json.dumps(response.data, indent=2, ensure_ascii=False)}</code>\n\n"

            success_message += "Выберите следующее действие:"

            await callback.message.edit_text(
                success_message,
                reply_markup=get_main_menu_keyboard()
            )
        else:
            error_message = (
                f" <b>Ошибка отправки</b>\n\n"
                f" <b>{shop.name}</b>\n"
                f" Попытка отправки: <b>{count} продуктов</b>\n"
                f" Ошибка: <b>{response.error_message}</b>\n\n"
                "Возможные причины:\n"
                "• Неверный API ключ\n"
                "• Проблемы с подключением\n"
                "• Сервер недоступен\n\n"
                "Выберите действие:"
            )

            await callback.message.edit_text(
                error_message,
                reply_markup=get_main_menu_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при отправке продуктов: {e}")
        await callback.message.edit_text(
            f" Произошла непредвиденная ошибка: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("test_api_"))
async def callback_test_api(callback: CallbackQuery):
    """Тестирование подключения к API магазина"""
    shop_id = int(callback.data.replace("test_api_", ""))

    await callback.message.edit_text(
        " Проверка подключения к API...\n"
        "Пожалуйста, подождите."
    )

    try:
        db = SessionLocal()
        shop = get_shop_by_id(db, shop_id)
        db.close()

        if not shop:
            await callback.message.edit_text(
                " Магазин не найден.",
                reply_markup=get_main_menu_keyboard()
            )
            await callback.answer()
            return

        # Тестируем подключение
        response = await api_client.test_connection(shop.client_id, shop.api_key)

        if response.success:
            success_message = (
                f" <b>API подключение успешно!</b>\n\n"
                f" <b>{shop.name}</b>\n"
                f" Client ID: <code>{shop.client_id}</code>\n"
                f" Статус: <b>Соединение установлено</b>\n\n"
                "Теперь вы можете отправлять данные на API."
            )
        else:
            success_message = (
                f" <b>Ошибка подключения к API</b>\n\n"
                f" <b>{shop.name}</b>\n"
                f" Client ID: <code>{shop.client_id}</code>\n"
                f" Ошибка: <b>{response.error_message}</b>\n\n"
                "Проверьте:\n"
                "• Корректность API ключа\n"
                "• Доступность сервера\n"
                "• Настройки магазина"
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Отправить продукты", callback_data=f"send_products_{shop_id}"),
                InlineKeyboardButton(text=" Проверить снова", callback_data=f"test_api_{shop_id}")
            ],
            [
                InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
            ]
        ])

        await callback.message.edit_text(success_message, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при тестировании API: {e}")
        await callback.message.edit_text(
            f" Произошла ошибка при проверке API: {str(e)}",
            reply_markup=get_main_menu_keyboard()
        )

    await callback.answer()

@router.callback_query(F.data.startswith("send_products_"))
async def callback_send_products(callback: CallbackQuery):
    """Отправка товаров на API выбранного магазина"""
    try:
        shop_id = int(callback.data.replace("send_products_", ""))

        # Получаем данные магазина
        db = SessionLocal()
        try:
            shop = get_shop_by_id(db, shop_id)
            if not shop:
                await callback.message.edit_text(
                    " <b>Магазин не найден</b>\n\n"
                    "Магазин был удален или недоступен."
                )
                return

            if not shop.is_active:
                await callback.message.edit_text(
                    f" <b>Магазин '{shop.name}' не активен</b>\n\n"
                    "Активируйте магазин через /shops перед отправкой товаров."
                )
                return

        except Exception as e:
            logger.error(f"Ошибка при получении магазина {shop_id}: {e}")
            await callback.message.edit_text(" Ошибка при работе с базой данных")
            return
        finally:
            db.close()

        # Ищем временный файл с товарами для этого магазина
        import glob
        import os
        temp_files = glob.glob(f"/tmp/products_{callback.from_user.id}_{shop_id}_*.json")

        if not temp_files:
            await callback.message.edit_text(
                f" <b>Файл с товарами не найден</b>\n\n"
                f"Загрузите новый Excel файл с товарами для магазина '{shop.name}'."
            )
            return

        # Берем самый свежий файл
        latest_file = max(temp_files, key=os.path.getctime)

        # Читаем данные товаров
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла товаров {latest_file}: {e}")
            await callback.message.edit_text(" Ошибка при чтении данных товаров")
            return

        products = products_data.get("products", {})
        client_id = products_data.get("client_id")

        if not products:
            await callback.message.edit_text(" В файле не найдены товары для отправки")
            return

        # Отправляем уведомление о начале отправки
        await callback.message.edit_text(
            f" <b>Отправка товаров на API...</b>\n\n"
            f" <b>Магазин:</b> {shop.name}\n"
            f" <b>Товаров:</b> {len(products)}\n"
            f" <b>Client ID:</b> {client_id}\n\n"
            f"Пожалуйста, подождите..."
        )

        # Отправляем товары на API
        from bot.services.api_client import api_client

        # Отправляем продукты как словарь (уже в правильном формате)
        response = await api_client.send_products(client_id, shop.api_key, products)

        if response.success:
            logger.info(f"Товары успешно отправлены для магазина {shop.name} (shop_id: {shop_id}), отправлено товаров: {len(products)}")
            
            # Удаляем временный файл после успешной отправки
            try:
                os.remove(latest_file)
            except Exception as cleanup_error:
                logger.warning(f"Не удалось удалить временный файл {latest_file}: {cleanup_error}")

            success_text = (
                f" <b>Товары успешно отправлены!</b>\n\n"
                f" <b>Магазин:</b> {shop.name}\n"
                f" <b>Отправлено товаров:</b> {len(products)}\n"
                f" <b>Client ID:</b> {client_id}\n"
                f" <b>Статус ответа:</b> HTTP {response.status_code}\n"
            )
            
            # Если есть данные в ответе, показываем их
            if response.data:
                success_text += f"\n <b>Ответ сервера:</b>\n"
                response_str = json.dumps(response.data, indent=2, ensure_ascii=False)
                if len(response_str) > 500:
                    success_text += f"<code>{response_str[:500]}...</code>"
                else:
                    success_text += f"<code>{response_str}</code>"
            
            success_text += (
                f"\n\nВсе товары были успешно переданы в систему магазина."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=" Загрузить новый файл", callback_data="upload_excel"),
                    InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
                ]
            ])
            
            await callback.message.edit_text(success_text, reply_markup=keyboard)
        else:
            # Формируем детальное сообщение об ошибке
            error_text = (
                f" <b>Ошибка отправки товаров</b>\n\n"
                f" <b>Магазин:</b> {shop.name}\n"
                f" <b>Товаров:</b> {len(products)}\n"
                f" <b>Client ID:</b> {client_id}\n\n"
                f" <b>HTTP Статус:</b> {response.status_code}\n"
                f" <b>Тип ошибки:</b> {response.error_type if response.error_type else 'Неизвестно'}\n"
                f" <b>Сообщение:</b> {response.error_message}\n"
            )
            
            # Добавляем информацию о сыром ответе если доступна
            if response.data and isinstance(response.data, dict) and 'raw_response' in response.data:
                raw_response = response.data['raw_response']
                if len(raw_response) > 200:
                    error_text += f" <b>Ответ сервера:</b> <code>{raw_response[:200]}...</code>\n"
                else:
                    error_text += f" <b>Ответ сервера:</b> <code>{raw_response}</code>\n"
            
            error_text += (
                f"\n<b>Рекомендации:</b>\n"
                f"• Проверьте API ключ магазина\n"
                f"• Проверьте подключение к интернету\n"
                f"• Убедитесь, что сервер доступен\n"
                f"• Повторите попытку позже\n\n"
                f"Выберите действие:"
            )

            # Добавляем кнопку для повторной отправки
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text=" Повторить отправку", callback_data=f"send_products_{shop_id}"),
                    InlineKeyboardButton(text=" Показать товары", callback_data=f"show_products_{shop_id}")
                ],
                [
                    InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
                ]
            ])

            await callback.message.edit_text(error_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при отправке товаров: {e}")
        await callback.message.edit_text(
            " <b>Критическая ошибка</b>\n\n"
            "Произошла непредвиденная ошибка при отправке товаров.\n"
            "Попробуйте позже или обратитесь к администратору."
        )

    await callback.answer()

@router.callback_query(F.data.startswith("show_products_"))
async def callback_show_products(callback: CallbackQuery):
    """Показ товаров из временного файла"""
    try:
        shop_id = int(callback.data.replace("show_products_", ""))

        # Получаем данные магазина
        db = SessionLocal()
        try:
            shop = get_shop_by_id(db, shop_id)
            if not shop:
                await callback.message.edit_text(
                    " <b>Магазин не найден</b>\n\n"
                    "Магазин был удален или недоступен."
                )
                return

        except Exception as e:
            logger.error(f"Ошибка при получении магазина {shop_id}: {e}")
            await callback.message.edit_text(" Ошибка при работе с базой данных")
            return
        finally:
            db.close()

        # Ищем временный файл с товарами для этого магазина
        import glob
        import os
        temp_files = glob.glob(f"/tmp/products_{callback.from_user.id}_{shop_id}_*.json")

        if not temp_files:
            await callback.message.edit_text(
                f" <b>Файл с товарами не найден</b>\n\n"
                f"Загрузите новый Excel файл с товарами для магазина '{shop.name}'."
            )
            return

        # Берем самый свежий файл
        latest_file = max(temp_files, key=os.path.getctime)

        # Читаем данные товаров
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                products_data = json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при чтении файла товаров {latest_file}: {e}")
            await callback.message.edit_text(" Ошибка при чтении данных товаров")
            return

        products = products_data.get("products", {})
        file_info = products_data.get("file_info", {})

        if not products:
            await callback.message.edit_text(" В файле не найдены товары")
            return

        # Формируем текст с товарами
        products_text = f" <b>Товары для отправки</b>\n\n"
        products_text += f" <b>Магазин:</b> {shop.name}\n"
        products_text += f" <b>Client ID:</b> {products_data.get('client_id')}\n"
        products_text += f" <b>Всего товаров:</b> {len(products)}\n\n"

        products_text += "<b>Список товаров:</b>\n"
        for i, (name, quantity) in enumerate(products.items(), 1):
            products_text += f"{i:2d}. {name} - {quantity} шт.\n"
            if i >= 20:  # Ограничиваем список первыми 20 товарами
                products_text += f"... и еще {len(products) - 20} товаров\n"
                break

        # Добавляем информацию о файле
        if file_info:
            products_text += f"\n <b>Файл:</b> {file_info.get('filename', 'N/A')}\n"
            products_text += f" <b>Обработан:</b> {file_info.get('processed_at', 'N/A')[:19]}\n"

        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=" Отправить на API", callback_data=f"send_products_{shop_id}"),
                InlineKeyboardButton(text="Удалить файл", callback_data=f"delete_products_{shop_id}")
            ],
            [
                InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
            ]
        ])

        await callback.message.edit_text(products_text, reply_markup=keyboard)

    except Exception as e:
        logger.error(f"Ошибка при показе товаров: {e}")
        await callback.message.edit_text(
            " <b>Ошибка при показе товаров</b>\n\n"
            "Произошла ошибка при отображении списка товаров."
        )

    await callback.answer()

@router.callback_query(F.data.startswith("delete_products_"))
async def callback_delete_products(callback: CallbackQuery):
    """Удаление временного файла с товарами"""
    try:
        shop_id = int(callback.data.replace("delete_products_", ""))

        # Получаем данные магазина
        db = SessionLocal()
        try:
            shop = get_shop_by_id(db, shop_id)
            shop_name = shop.name if shop else "Неизвестный магазин"
        except Exception as e:
            logger.error(f"Ошибка при получении магазина {shop_id}: {e}")
            shop_name = "Неизвестный магазин"
        finally:
            db.close()

        # Удаляем все временные файлы для этого магазина
        import glob
        import os
        temp_files = glob.glob(f"/tmp/products_{callback.from_user.id}_{shop_id}_*.json")

        deleted_count = 0
        for file_path in temp_files:
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                logger.error(f"Ошибка при удалении файла {file_path}: {e}")

        await callback.message.edit_text(
            f"<b>Файлы удалены</b>\n\n"
            f" <b>Магазин:</b> {shop_name}\n"
            f" <b>Удалено файлов:</b> {deleted_count}\n\n"
            f"Загрузите новый Excel файл для продолжения работы."
        )

    except Exception as e:
        logger.error(f"Ошибка при удалении файлов товаров: {e}")
        await callback.message.edit_text(
            " <b>Ошибка при удалении файлов</b>\n\n"
            "Произошла ошибка при удалении временных файлов."
        )

    await callback.answer()

def register_handlers(dp):
    """Регистрация всех обработчиков в диспетчере"""
    dp.include_router(router)
