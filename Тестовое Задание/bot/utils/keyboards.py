from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.models import Shop

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура с основными командами"""
    keyboard = [
        [
            InlineKeyboardButton(text=" Добавить магазин", callback_data="add_shop"),
            InlineKeyboardButton(text=" Мои магазины", callback_data="shops")
        ],
        [
            InlineKeyboardButton(text=" Загрузить Excel", callback_data="upload_excel"),
            InlineKeyboardButton(text=" Отправить на API", callback_data="send_to_api")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения действий"""
    keyboard = [
        [
            InlineKeyboardButton(text=" Да", callback_data="confirm_yes"),
            InlineKeyboardButton(text=" Нет", callback_data="confirm_no")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_shops_keyboard(shops: List[Shop], current_page: int = 0, per_page: int = 5) -> InlineKeyboardMarkup:
    """Клавиатура со списком магазинов с пагинацией"""
    keyboard = []

    # Вычисляем диапазон магазинов для текущей страницы
    start_idx = current_page * per_page
    end_idx = start_idx + per_page
    page_shops = shops[start_idx:end_idx]

    # Добавляем кнопки магазинов
    for shop in page_shops:
        status_emoji = "" if shop.is_active else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status_emoji} {shop.name}",
                callback_data=f"shop_{shop.id}"
            )
        ])

    # Добавляем кнопки навигации
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text=" Назад", callback_data=f"page_{current_page - 1}")
        )

    if end_idx < len(shops):
        nav_buttons.append(
            InlineKeyboardButton(text=" Вперед ", callback_data=f"page_{current_page + 1}")
        )

    if nav_buttons:
        keyboard.append(nav_buttons)

    # Кнопка возврата в главное меню
    keyboard.append([
        InlineKeyboardButton(text=" Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_shop_actions_keyboard(shop_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с конкретным магазином"""
    keyboard = [
        [
            InlineKeyboardButton(text=" Переключить статус", callback_data=f"toggle_{shop_id}"),
            InlineKeyboardButton(text=" Редактировать", callback_data=f"edit_{shop_id}")
        ],
        [
            InlineKeyboardButton(text=" Отправить продукты", callback_data=f"send_products_{shop_id}"),
            InlineKeyboardButton(text=" Проверить API", callback_data=f"test_api_{shop_id}")
        ],
        [
            InlineKeyboardButton(text=" Удалить", callback_data=f"delete_{shop_id}")
        ],
        [
            InlineKeyboardButton(text=" Назад к списку", callback_data="back_to_shops")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_products_count_keyboard(shop_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора количества продуктов для отправки"""
    keyboard = [
        [
            InlineKeyboardButton(text=" 3 тестовых продукта", callback_data=f"send_count_{shop_id}_3"),
            InlineKeyboardButton(text=" 5 тестовых продуктов", callback_data=f"send_count_{shop_id}_5")
        ],
        [
            InlineKeyboardButton(text=" 10 тестовых продуктов", callback_data=f"send_count_{shop_id}_10"),
            InlineKeyboardButton(text=" Ввести JSON", callback_data=f"send_json_{shop_id}")
        ],
        [
            InlineKeyboardButton(text=" Отмена", callback_data=f"shop_{shop_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
