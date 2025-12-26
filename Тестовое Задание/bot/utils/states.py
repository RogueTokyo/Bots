from typing import Final
from aiogram.fsm.state import State, StatesGroup

class ShopStates(StatesGroup):
    """Состояния для работы с магазинами"""

    # Состояния для добавления магазина
    waiting_for_shop_name: Final[State] = State()
    waiting_for_client_id: Final[State] = State()
    waiting_for_api_key: Final[State] = State()
    confirming_shop_creation: Final[State] = State()

    # Состояния для управления магазинами
    selecting_shop: Final[State] = State()
    shop_action: Final[State] = State()

    # Состояния для отправки данных на API
    sending_products: Final[State] = State()
    waiting_for_products_data: Final[State] = State()
