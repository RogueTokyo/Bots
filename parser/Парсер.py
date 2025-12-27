import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import hashlib
import time
import re

from utils import load_env_from_file, require_env

from aiogram import Bot, Dispatcher, F  # pyright: ignore[reportMissingImports]
from aiogram.client.default import DefaultBotProperties  # pyright: ignore[reportMissingImports]
from aiogram.enums import ParseMode  # pyright: ignore[reportMissingImports]
from aiogram.filters import Command  # pyright: ignore[reportMissingImports]
from aiogram.fsm.context import FSMContext  # pyright: ignore[reportMissingImports]
from aiogram.fsm.state import State, StatesGroup  # pyright: ignore[reportMissingImports]
from aiogram.fsm.storage.memory import MemoryStorage  # pyright: ignore[reportMissingImports]
from aiogram.types import Message, CallbackQuery  # pyright: ignore[reportMissingImports]
from aiogram.utils.keyboard import InlineKeyboardBuilder  # pyright: ignore[reportMissingImports]
# Импорт telethon
TELETHON_AVAILABLE = False
TelegramClient = None
RPCError = None
StringSession = None

try:
    from telethon import TelegramClient
    from telethon.errors import RPCError
    from telethon.sessions import StringSession
    TELETHON_AVAILABLE = True
except ImportError:
    print("⚠️  Telethon не установлен. Установите: pip install telethon")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("parser-bot")

# Загружаем конфигурацию при импорте модуля
load_env_from_file('config.env')


BOT_TOKEN = require_env("TG_BOT_TOKEN")
APP_ID = int(require_env("TG_APP_ID"))
APP_HASH = require_env("TG_APP_HASH")

# Настройки Telethon
if TELETHON_AVAILABLE:
    session_string = os.getenv("TG_SESSION_STRING")
    session_name = os.getenv("TG_SESSION_NAME", "parser_session")

    if session_string and session_string.strip():
        try:
            telethon_client = TelegramClient(StringSession(session_string), APP_ID, APP_HASH)
        except ValueError as e:
            print(f"⚠️  Некорректная строковая сессия: {e}")
            telethon_client = TelegramClient(session_name, APP_ID, APP_HASH)
    else:
        telethon_client = TelegramClient(session_name, APP_ID, APP_HASH)
else:
    telethon_client = None

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Папка для хранения запросов
REQUESTS_DIR = Path("requests")
REQUESTS_DIR.mkdir(exist_ok=True)

# Папка для кеширования результатов поиска
CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

# Время жизни кеша в секундах (1 час)
CACHE_TTL = 3600

# Константы для текстовых ответов
QUICK_START_TEXT = """📖 <b>Быстрый старт</b>

1️⃣ <b>Быстрый формат:</b>
Отправьте сообщение вида:
<code>python разработка @python @django</code>

2️⃣ <b>Пошаговый режим:</b>
• Отправьте ключевые слова
• Я спрошу каналы для поиска

3️⃣ <b>Результат:</b>
Запрос сохранится для обработки
Результаты придут позже"""

QUICK_FORMAT_TEXT = """⚡ <b>Быстрый формат</b>

<b>Пример:</b>
<code>python разработка @python @django</code>

<b>Как это работает:</b>
• Все в одном сообщении
• Сначала ключевые слова
• Затем @каналы через пробел

<b>Дополнительные примеры:</b>
• <code>новости технологий @technews</code>
• <code>машинное обучение AI @ml @datascience</code>"""

STEP_FORMAT_TEXT = """📝 <b>Пошаговый формат</b>

<b>Как это работает:</b>
1️⃣ Отправьте ключевые слова
2️⃣ Я спрошу каналы
3️⃣ Отправьте список каналов

<b>Пример:</b>
<b>Вы:</b> python разработка
<b>Бот:</b> Теперь укажите каналы...
<b>Вы:</b> @python @django

<b>Преимущества:</b>
• Не нужно запоминать формат
• Можно исправить ошибки
• Подходит для сложных запросов"""

FAQ_TEXT = """❓ <b>Часто задаваемые вопросы</b>

<b>❓ Как посмотреть мои запросы?</b>
• Используйте кнопку "📝 Мои запросы"
• Или команду /list

<b>❓ Что происходит с запросами?</b>
• Запросы сохраняются в JSON файлы
• Обрабатываются отдельно
• Результаты приходят позже

<b>❓ Какие каналы поддерживаются?</b>
• Публичные каналы
• Форматы: "@username", "t.me/канал"
• Не приватные каналы

<b>❓ Максимальное количество?</b>
• 10 ключевых слов
• 5 каналов за раз
• Неограниченное количество запросов

<b>❓ Нужна помощь или есть вопросы?</b>
• Напишите разработчику: @RogueTokyo"""

NEW_REQUEST_TEXT = """🔍 <b>Создание нового запроса</b>

Выберите способ создания запроса:

1️⃣ <b>Быстрый формат:</b>
Отправьте сообщение вида:
<code>python разработка @python @django</code>

2️⃣ <b>Пошаговый режим:</b>
Просто отправьте ключевые слова,
и я спрошу каналы.

<b>💡 Совет:</b> Используйте быстрый формат
для простых запросов!"""


def create_keyboard(buttons: List[Dict[str, str]], adjust: int = 1, back_button: bool = False) -> InlineKeyboardBuilder:
    """Универсальная функция создания клавиатуры."""
    builder = InlineKeyboardBuilder()

    for button in buttons:
        builder.button(text=button["text"], callback_data=button["callback_data"])

    if back_button:
        builder.button(text="🏠 Назад в меню", callback_data="back_to_menu")

    builder.adjust(adjust)
    return builder.as_markup()


def get_main_menu_keyboard():
    """Создает главное меню с кнопками."""
    buttons = [
        {"text": "📋 Справка", "callback_data": "help"},
        {"text": "📝 Мои запросы", "callback_data": "list"},
        {"text": "🔍 Новый запрос", "callback_data": "new_request"},
        {"text": "🔎 Выполнить поиск", "callback_data": "execute_search"},
        {"text": "📊 Статистика", "callback_data": "stats"}
    ]
    return create_keyboard(buttons, adjust=2)


def get_back_menu_keyboard():
    """Создает кнопку возврата в меню."""
    return create_keyboard([], back_button=True)


def create_search_results_keyboard(request_timestamp: str, total_results: int, current_page: int = 1, per_page: int = 5, current_format: str = "text") -> InlineKeyboardBuilder:
    """Создает клавиатуру для результатов поиска с пагинацией."""
    builder = InlineKeyboardBuilder()

    total_pages = (total_results + per_page - 1) // per_page  # Ceiling division

    # Кнопки пагинации (если больше одной страницы)
    if total_pages > 1:
        if current_page > 1:
            builder.button(text="⬅️ Назад", callback_data=f"page_{current_page-1}_{request_timestamp}")

        builder.button(text=f"📄 {current_page}/{total_pages}", callback_data="ignore")

        if current_page < total_pages:
            builder.button(text="➡️ Далее", callback_data=f"page_{current_page+1}_{request_timestamp}")

    # Кнопки переключения формата
    if current_format != "table":
        builder.button(text="📊 Таблица", callback_data=f"show_table_results_{request_timestamp}")
    if current_format != "text":
        builder.button(text="📝 Текст", callback_data=f"show_text_results_{request_timestamp}")

    # Кнопки действий
    builder.button(text="🔍 Новый поиск", callback_data="new_request")
    builder.button(text="🏠 Главное меню", callback_data="back_to_menu")

    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()


def get_help_keyboard():
    """Создает клавиатуру для справки."""
    buttons = [
        {"text": "📖 Быстрый старт", "callback_data": "quick_start"},
        {"text": "📝 Форматы запросов", "callback_data": "request_formats"},
        {"text": "❓ FAQ", "callback_data": "faq"}
    ]
    return create_keyboard(buttons, back_button=True)


def get_request_formats_keyboard():
    """Создает клавиатуру для форматов запросов."""
    buttons = [
        {"text": "⚡ Быстрый формат", "callback_data": "format_quick"},
        {"text": "📝 Пошаговый формат", "callback_data": "format_step"}
    ]
    return create_keyboard(buttons, back_button=True)


class SearchForm(StatesGroup):
    keywords = State()
    channels = State()


@dataclass
class SearchRequest:
    user_id: int
    username: str
    keywords: List[str]
    channels: List[str]
    created_at: str


@dataclass
class SearchResult:
    """Результат поиска с релевантными предложениями."""
    channel: str
    message_id: int
    date: str
    snippet: str  # Релевантные предложения, содержащие ключевые слова
    link: str


def normalize_list(payload: str) -> List[str]:
    """Нормализует строку в список элементов."""
    if not payload or not payload.strip():
        return []

    raw = [item.strip() for item in payload.replace("\n", ",").split(",")]
    return [item for item in raw if item]


def validate_keywords(keywords: List[str]) -> List[str]:
    """Валидирует и очищает ключевые слова."""
    if not keywords:
        return []

    validated = []
    for kw in keywords:
        kw = kw.strip()
        if len(kw) < 2:
            continue  # Слишком короткие слова пропускаем
        if len(kw) > 50:
            kw = kw[:50]  # Ограничиваем длину
        validated.append(kw)

    return validated[:10]  # Максимум 10 ключевых слов


def validate_channels(channels: List[str]) -> List[str]:
    """Валидирует и нормализует каналы."""
    if not channels:
        return []

    validated = []
    for channel in channels:
        channel = channel.strip()
        if not channel:
            continue

        # Поддерживаем разные форматы каналов
        if channel.startswith('@'):
            validated.append(channel)
        elif channel.startswith('https://t.me/'):
            # Извлекаем username из ссылки
            username = channel.replace('https://t.me/', '').split('/')[0]
            if username:
                validated.append(f"@{username}")
        elif 't.me/' in channel:
            # Извлекаем username из ссылки
            parts = channel.split('t.me/')
            if len(parts) > 1:
                username = parts[1].split('/')[0]
                if username:
                    validated.append(f"@{username}")
        else:
            # Предполагаем, что это username
            validated.append(f"@{channel}")

    return validated[:5]  # Максимум 5 каналов


def load_user_requests(user_id: int) -> List[Dict[str, Any]]:
    """Загружает все запросы пользователя."""
    requests = []
    for file_path in REQUESTS_DIR.glob(f"request_{user_id}_*.json"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                requests.append(data)
        except Exception as e:
            logger.error(f"Ошибка чтения файла {file_path}: {e}")

    # Сортируем по дате создания (новые сверху)
    requests.sort(key=lambda x: x['created_at'], reverse=True)
    return requests


def format_user_requests_list(user_requests: List[Dict[str, Any]], max_requests: int = 10) -> str:
    """Форматирует список запросов пользователя для отображения."""
    if not user_requests:
        return "📭 <b>У вас пока нет сохраненных запросов.</b>\n\nСоздайте новый запрос или используйте команду /help для справки."

    response = "📋 <b>Ваши запросы:</b>\n\n"
    for i, req in enumerate(user_requests[:max_requests], 1):
        created = datetime.fromisoformat(req['created_at']).strftime("%d.%m.%Y %H:%M")
        response += f"{i}. <b>{created}</b>\n"
        response += f"🔍 {', '.join(req['keywords'])}\n"
        response += f"📺 {', '.join(req['channels'])}\n\n"

    if len(user_requests) > max_requests:
        response += f"... и ещё {len(user_requests) - max_requests} запросов"

    return response


async def ensure_telethon_connected() -> None:
    """Инициализирует подключение к Telegram через Telethon."""
    if not TELETHON_AVAILABLE:
        raise RuntimeError("Telethon не доступен. Установите: pip install telethon")

    if telethon_client is None:
        raise RuntimeError("Telethon client не инициализирован")

    if not telethon_client.is_connected():
        await telethon_client.connect()
    if not await telethon_client.is_user_authorized():
        msg = (
            "Telethon client не авторизован. "
            "Запустите скрипт интерактивно для авторизации или предоставьте TG_SESSION_STRING."
        )
        logger.error(msg)
        raise RuntimeError(msg)


def fuzzy_match_word(word: str, keyword: str) -> bool:
    """Проверяет, является ли слово похожим на ключевое слово."""
    word_lower = word.lower()
    keyword_lower = keyword.lower()

    # Точное совпадение
    if word_lower == keyword_lower:
        return True

    # Проверка на подстроку (ключевое слово содержится в слове)
    if keyword_lower in word_lower:
        return True

    # Проверка морфологических вариаций для русских слов
    # Убираем окончания для некоторых распространенных случаев
    endings = ['а', 'ы', 'ов', 'ей', 'ам', 'ами', 'ах', 'ом', 'ого', 'ому', 'им', 'ем', 'ого', 'ему', 'ими', 'ими', 'ой', 'ую', 'ю', 'ие', 'их', 'им', 'ыми', 'ая', 'яя', 'ое', 'ее', 'ие', 'ей', 'ую', 'юю', 'ие', 'их', 'им']

    for ending in endings:
        if word_lower == keyword_lower + ending:
            return True
        if keyword_lower.endswith(ending) and word_lower == keyword_lower[:-len(ending)]:
            return True

    # Проверка на похожие слова (расстояние Левенштейна <= 2 для коротких слов)
    if len(keyword) <= 6 and len(word) <= 8:
        def levenshtein_distance(s1: str, s2: str) -> int:
            if len(s1) < len(s2):
                return levenshtein_distance(s2, s1)
            if len(s2) == 0:
                return len(s1)

            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + 1
                    deletions = current_row[j] + 1
                    substitutions = previous_row[j] + (c1 != c2)
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row

            return previous_row[-1]

        distance = levenshtein_distance(word_lower, keyword_lower)
        if distance <= 2:  # Максимум 2 ошибки
            return True

    return False


def extract_relevant_sentences(text: str, keywords: List[str]) -> List[str]:
    """Извлекает предложения, содержащие ключевые слова или похожие слова."""
    if not text or not keywords:
        return []

    # Разбиваем текст на предложения
    sentence_pattern = r'(?<=[.!?])\s+'
    sentences = re.split(sentence_pattern, text.strip())

    relevant_sentences = []

    for sentence in sentences:
        sentence_lower = sentence.lower().strip()
        if not sentence_lower:
            continue

        # Разбиваем предложение на слова для более точного поиска
        words = re.findall(r'\b\w+\b', sentence_lower)

        # Проверяем, содержит ли предложение хотя бы одно ключевое слово или похожее
        has_match = False
        for word in words:
            for keyword in keywords:
                if fuzzy_match_word(word, keyword):
                    has_match = True
                    break
            if has_match:
                break

        if has_match:
            # Очищаем предложение от лишних пробелов
            clean_sentence = " ".join(sentence.split())
            if clean_sentence and len(clean_sentence) > 10:  # Минимум 10 символов
                relevant_sentences.append(clean_sentence)

    return relevant_sentences


async def search_channel_messages(
    channels: List[str],
    keywords: List[str],
    limit: int = 50,
    force_refresh: bool = False
) -> List[SearchResult]:
    """Ищет сообщения по каналам с заданными ключевыми словами."""
    if not TELETHON_AVAILABLE:
        logger.error("Telethon не доступен для поиска")
        return []

    # Проверяем кеш (если не принудительное обновление)
    cache_key = get_cache_key(channels, keywords, limit)
    if not force_refresh:
        cached_results = load_cached_results(cache_key)
        if cached_results is not None:
            return cached_results

    # Выполняем новый поиск
    await ensure_telethon_connected()

    lowercase_keywords = [kw.lower() for kw in keywords]
    results: List[SearchResult] = []

    # Распределяем лимит между каналами
    per_channel_limit = max(50, limit * 2)  # Минимум 50 сообщений на канал для поиска

    for channel in channels:
        if len(results) >= limit:
            break  # Достигли общего лимита

        try:
            entity = await telethon_client.get_entity(channel)
        except RPCError as exc:
            logger.warning("Не удалось получить доступ к каналу %s: %s", channel, exc)
            continue

        username = getattr(entity, "username", None)
        link_template = f"https://t.me/{username}" if username else ""
        channel_title = getattr(entity, "title", channel)

        logger.info("Поиск в канале: %s", channel_title)

        try:
            async for message in telethon_client.iter_messages(entity, limit=per_channel_limit):
                text = message.message or ""
                if not text:
                    continue

                # Извлекаем релевантные предложения
                relevant_sentences = extract_relevant_sentences(text, lowercase_keywords)
                if not relevant_sentences:
                    continue

                # Формируем snippet из релевантных предложений
                snippet = " ".join(relevant_sentences[:3])  # Максимум 3 предложения
                if len(snippet) > 200:
                    snippet = snippet[:197] + "..."

                link = f"{link_template}/{message.id}" if link_template else "—"
                results.append(
                    SearchResult(
                        channel=channel_title,
                        message_id=message.id,
                        date=message.date.strftime("%d.%m.%y %H:%M"),
                        snippet=snippet,
                        link=link,
                    )
                )

                if len(results) >= limit:
                    break  # Достигли общего лимита

        except Exception as exc:
            logger.error("Ошибка при обработке канала %s: %s", channel, exc)
            continue

    logger.info("Найдено результатов: %d", len(results))

    # Сохраняем результаты в кеш
    save_cached_results(cache_key, results)

    return results


def format_search_results(results: List[SearchResult], page: int = 1, per_page: int = 5, use_table: bool = False) -> str:
    """Форматирует результаты поиска в читаемый текст или таблицу."""
    if use_table:
        return format_search_results_as_table(results, page, per_page)
    else:
        return format_search_results_as_text(results, page, per_page)


def format_search_results_as_text(results: List[SearchResult], page: int = 1, per_page: int = 5) -> str:
    """Форматирует результаты поиска в текстовом виде."""
    if not results:
        return "❌ <b>Совпадений не найдено</b>\n\nПопробуйте изменить ключевые слова или каналы."

    total_results = len(results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = results[start_idx:end_idx]

    response = f"🔍 <b>Результаты поиска</b> ({total_results} найдено, стр. {page})\n\n"

    for i, result in enumerate(page_results, start_idx + 1):
        response += f"<b>{i}.</b> {result.channel}\n"
        response += f"📅 {result.date}\n"
        response += f"💬 {result.snippet}\n"
        if result.link != "—":
            response += f"🔗 {result.link}\n"
        response += "\n"

    return response


def format_search_results_as_table(results: List[SearchResult], page: int = 1, per_page: int = 5) -> str:
    """Форматирует результаты поиска в виде Markdown таблицы."""
    if not results:
        return "❌ <b>Совпадений не найдено</b>\n\nПопробуйте изменить ключевые слова или каналы."

    total_results = len(results)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_results = results[start_idx:end_idx]

    response = f"📊 <b>Результаты поиска</b> ({total_results} найдено, стр. {page})\n\n"

    # Заголовки таблицы
    response += "| # | Канал | Дата | Текст | Ссылка |\n"
    response += "|----|-------|------|-------|--------|\n"

    # Данные таблицы
    for i, result in enumerate(page_results, start_idx + 1):
        # Экранируем специальные символы для Markdown
        channel = result.channel.replace("|", "\\|").replace("\n", " ")
        snippet = result.snippet.replace("|", "\\|").replace("\n", " ")
        link = result.link if result.link != "—" else "—"

        # Ограничиваем длину для читаемости
        if len(snippet) > 50:
            snippet = snippet[:47] + "..."
        if len(channel) > 20:
            channel = channel[:17] + "..."

        response += f"| {i} | {channel} | {result.date} | {snippet} | {link} |\n"

    return response


def save_request(request: SearchRequest) -> None:
    """Сохраняет запрос в JSON файл."""
    filename = f"request_{request.user_id}_{int(datetime.now().timestamp())}.json"
    filepath = REQUESTS_DIR / filename

    data = {
        "user_id": request.user_id,
        "username": request.username or "unknown",
        "keywords": request.keywords,
        "channels": request.channels,
        "created_at": request.created_at
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"Запрос сохранен: {filepath}")


def get_cache_key(channels: List[str], keywords: List[str], limit: int) -> str:
    """Генерирует ключ кеша на основе параметров поиска."""
    # Сортируем для консистентности
    sorted_channels = sorted(channels)
    sorted_keywords = sorted(keywords)

    # Создаем строку для хеширования
    cache_string = f"{sorted_channels}_{sorted_keywords}_{limit}"
    return hashlib.md5(cache_string.encode()).hexdigest()


def load_cached_results(cache_key: str) -> Optional[List[SearchResult]]:
    """Загружает результаты из кеша, если они актуальны."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Проверяем время жизни кеша
        if time.time() - data['timestamp'] > CACHE_TTL:
            # Кеш устарел, удаляем файл
            cache_file.unlink()
            return None

        # Преобразуем данные обратно в SearchResult объекты
        results = []
        for item in data['results']:
            results.append(SearchResult(**item))

        logger.info(f"Загружены результаты из кеша: {len(results)} результатов")
        return results

    except Exception as e:
        logger.warning(f"Ошибка чтения кеша {cache_key}: {e}")
        return None


def save_cached_results(cache_key: str, results: List[SearchResult]) -> None:
    """Сохраняет результаты в кеш."""
    cache_file = CACHE_DIR / f"{cache_key}.json"

    try:
        # Преобразуем SearchResult объекты в словари
        results_data = []
        for result in results:
            results_data.append({
                'channel': result.channel,
                'message_id': result.message_id,
                'date': result.date,
                'snippet': result.snippet,
                'link': result.link
            })

        data = {
            'timestamp': time.time(),
            'results': results_data
        }

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Результаты сохранены в кеш: {cache_key}")

    except Exception as e:
        logger.warning(f"Ошибка сохранения в кеш {cache_key}: {e}")


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "🎯 <b>Парсер Telegram каналов</b>\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=get_main_menu_keyboard()
    )


@dp.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery) -> None:
    """Обработчик кнопки возврата в меню."""
    await callback.message.edit_text(
        "🎯 <b>Парсер Telegram каналов</b>\n\n"
        "Выберите действие в меню ниже:",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery) -> None:
    """Обработчик кнопки справки."""
    await callback.message.edit_text(
        "📋 <b>Справка по использованию</b>\n\n"
        "Выберите раздел справки:",
        reply_markup=get_help_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "quick_start")
async def callback_quick_start(callback: CallbackQuery) -> None:
    """Обработчик быстрого старта."""
    await callback.message.edit_text(QUICK_START_TEXT, reply_markup=get_back_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "request_formats")
async def callback_request_formats(callback: CallbackQuery) -> None:
    """Обработчик форматов запросов."""
    await callback.message.edit_text(
        "📝 <b>Форматы запросов</b>\n\n"
        "Выберите формат для подробной информации:",
        reply_markup=get_request_formats_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "format_quick")
async def callback_format_quick(callback: CallbackQuery) -> None:
    """Обработчик быстрого формата."""
    await callback.message.edit_text(QUICK_FORMAT_TEXT, reply_markup=get_back_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "format_step")
async def callback_format_step(callback: CallbackQuery) -> None:
    """Обработчик пошагового формата."""
    await callback.message.edit_text(STEP_FORMAT_TEXT, reply_markup=get_back_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "faq")
async def callback_faq(callback: CallbackQuery) -> None:
    """Обработчик FAQ."""
    await callback.message.edit_text(FAQ_TEXT, reply_markup=get_back_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "list")
async def callback_list(callback: CallbackQuery) -> None:
    """Обработчик кнопки списка запросов."""
    user_requests = load_user_requests(callback.from_user.id)
    response = format_user_requests_list(user_requests)

    await callback.message.edit_text(response, reply_markup=get_back_menu_keyboard())
    await callback.answer()


@dp.callback_query(F.data == "execute_search")
async def callback_execute_search(callback: CallbackQuery) -> None:
    """Обработчик кнопки выполнения поиска."""
    user_requests = load_user_requests(callback.from_user.id)

    if not user_requests:
        await callback.message.edit_text(
            "❌ <b>Нет сохраненных запросов</b>\n\n"
            "Сначала создайте запрос через кнопку \"🔍 Новый запрос\".",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    # Берем последний запрос
    latest_request = user_requests[0]

    await callback.message.edit_text(
        f"🔄 <b>Обновляю поиск...</b>\n\n"
        f"📝 Ключевые слова: {', '.join(latest_request['keywords'])}\n"
        f"📺 Каналы: {', '.join(latest_request['channels'])}\n\n"
        f"⏳ Поиск в реальном времени..."
    )
    await callback.answer()

    try:
        # Выполняем поиск с принудительным обновлением
        results = await search_channel_messages(
            latest_request['channels'],
            latest_request['keywords'],
            limit=50,  # Ограничиваем для быстрого поиска
            force_refresh=True
        )

        # Форматируем и отправляем результаты (по умолчанию в текстовом виде)
        response = format_search_results(results, page=1, per_page=5, use_table=False)

        # Создаем клавиатуру с результатами
        markup = create_search_results_keyboard(
            latest_request['created_at'],
            total_results=len(results),
            current_page=1,
            per_page=5,
            current_format="text"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при выполнении поиска: {e}")
        await callback.message.edit_text(
            f"❌ <b>Ошибка при выполнении поиска:</b>\n\n{str(e)}\n\n"
            "Возможные причины:\n"
            "• Проблемы с подключением к Telegram\n"
            "• Недоступность каналов\n"
            "• Превышен лимит запросов\n"
            "• Проблемы с авторизацией Telethon",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data.startswith("show_table_results_"))
async def callback_show_table_results(callback: CallbackQuery) -> None:
    """Обработчик показа результатов в табличном формате."""
    # Извлекаем timestamp из callback_data
    timestamp = callback.data.replace("show_table_results_", "")

    # Находим соответствующий запрос
    user_requests = load_user_requests(callback.from_user.id)
    request_data = None

    for req in user_requests:
        if req['created_at'] == timestamp:
            request_data = req
            break

    if not request_data:
        await callback.message.edit_text(
            "❌ Запрос не найден.",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text("🔄 Загружаю результаты в табличном формате...")
    await callback.answer()

    try:
        # Выполняем поиск
        results = await search_channel_messages(
            request_data['channels'],
            request_data['keywords'],
            limit=50,
            force_refresh=True
        )

        # Форматируем в виде таблицы
        response = format_search_results(results, page=1, per_page=10, use_table=True)

        # Создаем клавиатуру для табличных результатов
        markup = create_search_results_keyboard(
            timestamp,
            total_results=len(results),
            current_page=1,
            per_page=5,
            current_format="table"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке табличных результатов: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке результатов: {str(e)}",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data.startswith("show_text_results_"))
async def callback_show_text_results(callback: CallbackQuery) -> None:
    """Обработчик показа результатов в текстовом формате."""
    # Извлекаем timestamp из callback_data
    timestamp = callback.data.replace("show_text_results_", "")

    # Находим соответствующий запрос
    user_requests = load_user_requests(callback.from_user.id)
    request_data = None

    for req in user_requests:
        if req['created_at'] == timestamp:
            request_data = req
            break

    if not request_data:
        await callback.message.edit_text(
            "❌ Запрос не найден.",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text("🔄 Загружаю результаты в текстовом формате...")
    await callback.answer()

    try:
        # Выполняем поиск
        results = await search_channel_messages(
            request_data['channels'],
            request_data['keywords'],
            limit=50,
            force_refresh=True
        )

        # Форматируем в текстовом виде
        response = format_search_results(results, page=1, per_page=10, use_table=False)

        # Создаем клавиатуру для текстовых результатов
        markup = create_search_results_keyboard(
            timestamp,
            total_results=len(results),
            current_page=1,
            per_page=5,
            current_format="text"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке текстовых результатов: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке результатов: {str(e)}",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data.startswith("show_all_table_results_"))
async def callback_show_all_table_results(callback: CallbackQuery) -> None:
    """Обработчик показа всех результатов в табличном формате."""
    # Извлекаем timestamp из callback_data
    timestamp = callback.data.replace("show_all_table_results_", "")

    # Находим соответствующий запрос
    user_requests = load_user_requests(callback.from_user.id)
    request_data = None

    for req in user_requests:
        if req['created_at'] == timestamp:
            request_data = req
            break

    if not request_data:
        await callback.message.edit_text(
            "❌ Запрос не найден.",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text("🔄 Загружаю все результаты в табличном формате...")
    await callback.answer()

    try:
        # Выполняем поиск с большим лимитом
        results = await search_channel_messages(
            request_data['channels'],
            request_data['keywords'],
            limit=200,  # Больше результатов
            force_refresh=True
        )

        response = format_search_results(results, page=1, per_page=20, use_table=True)  # Больше результатов в выводе

        # Создаем клавиатуру для всех табличных результатов
        markup = create_search_results_keyboard(
            timestamp,
            total_results=len(results),
            current_page=1,
            per_page=20,
            current_format="table"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке всех табличных результатов: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке результатов: {str(e)}",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data.startswith("show_all_results_"))
async def callback_show_all_results(callback: CallbackQuery) -> None:
    """Обработчик показа всех результатов поиска."""
    # Извлекаем timestamp из callback_data
    timestamp = callback.data.replace("show_all_results_", "")

    # Находим соответствующий запрос
    user_requests = load_user_requests(callback.from_user.id)
    request_data = None

    for req in user_requests:
        if req['created_at'] == timestamp:
            request_data = req
            break

    if not request_data:
        await callback.message.edit_text(
            "❌ Запрос не найден.",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text("🔄 Загружаю все результаты...")
    await callback.answer()

    try:
        # Выполняем поиск с большим лимитом
        results = await search_channel_messages(
            request_data['channels'],
            request_data['keywords'],
            limit=200,  # Больше результатов
            force_refresh=True
        )

        response = format_search_results(results, page=1, per_page=20, use_table=False)  # Больше результатов в выводе

        # Создаем клавиатуру для всех результатов
        markup = create_search_results_keyboard(
            timestamp,
            total_results=len(results),
            current_page=1,
            per_page=20,
            current_format="text"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при загрузке всех результатов: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке результатов: {str(e)}",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data == "ignore")
async def callback_ignore(callback: CallbackQuery) -> None:
    """Обработчик игнорируемых кнопок (индикаторы страниц)."""
    await callback.answer()


@dp.callback_query(F.data.startswith("page_"))
async def callback_pagination(callback: CallbackQuery) -> None:
    """Обработчик пагинации результатов поиска."""
    # Формат: page_{page_number}_{request_timestamp}
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("Некорректные данные пагинации")
        return

    try:
        page = int(parts[1])
        request_timestamp = "_".join(parts[2:])  # На случай, если timestamp содержит подчеркивания
    except ValueError:
        await callback.answer("Некорректный номер страницы")
        return

    # Находим соответствующий запрос
    user_requests = load_user_requests(callback.from_user.id)
    request_data = None

    for req in user_requests:
        if req['created_at'] == request_timestamp:
            request_data = req
            break

    if not request_data:
        await callback.message.edit_text(
            "❌ Запрос не найден.",
            reply_markup=get_back_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text("🔄 Загружаю страницу...")
    await callback.answer()

    try:
        # Выполняем поиск
        results = await search_channel_messages(
            request_data['channels'],
            request_data['keywords'],
            limit=50,
            force_refresh=True
        )

        # Форматируем результаты для текущей страницы
        response = format_search_results(results, page=page, per_page=5, use_table=False)

        # Создаем клавиатуру с пагинацией
        markup = create_search_results_keyboard(
            request_timestamp,
            total_results=len(results),
            current_page=page,
            per_page=5,
            current_format="text"
        )

        await callback.message.edit_text(response, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка при пагинации: {e}")
        await callback.message.edit_text(
            f"❌ Ошибка при загрузке страницы: {str(e)}",
            reply_markup=get_back_menu_keyboard()
        )


@dp.callback_query(F.data == "new_request")
async def callback_new_request(callback: CallbackQuery) -> None:
    """Обработчик кнопки нового запроса."""
    # Создаем клавиатуру только с кнопкой возврата в меню
    markup = get_back_menu_keyboard()

    await callback.message.edit_text(NEW_REQUEST_TEXT, reply_markup=markup)
    await callback.answer()


@dp.callback_query(F.data == "stats")
async def callback_stats(callback: CallbackQuery) -> None:
    """Обработчик кнопки статистики."""
    user_requests = load_user_requests(callback.from_user.id)

    # Собираем общую статистику
    total_requests = len(user_requests)
    total_keywords = sum(len(req['keywords']) for req in user_requests)
    total_channels = sum(len(req['channels']) for req in user_requests)

    # Уникальные каналы
    all_channels = set()
    for req in user_requests:
        all_channels.update(req['channels'])
    unique_channels = len(all_channels)

    # Последний запрос
    last_request = "Нет запросов"
    if user_requests:
        last_request = datetime.fromisoformat(max(req['created_at'] for req in user_requests)).strftime("%d.%m.%Y %H:%M")

    response = "📊 <b>Ваша статистика</b>\n\n"
    response += f"📝 Всего запросов: <b>{total_requests}</b>\n"
    response += f"🔍 Ключевых слов: <b>{total_keywords}</b>\n"
    response += f"📺 Каналов всего: <b>{total_channels}</b>\n"
    response += f"🌟 Уникальных каналов: <b>{unique_channels}</b>\n"
    response += f"🕒 Последний запрос: <b>{last_request}</b>\n\n"

    if total_requests > 0:
        avg_keywords = total_keywords / total_requests
        avg_channels = total_channels / total_requests
        response += f"📈 Среднее слов на запрос: <b>{avg_keywords:.1f}</b>\n"
        response += f"📈 Среднее каналов на запрос: <b>{avg_channels:.1f}</b>\n"
    else:
        response += "💡 <i>Создайте первый запрос!</i>"

    await callback.message.edit_text(response, reply_markup=get_back_menu_keyboard())
    await callback.answer()




@dp.message(Command("list"))
async def cmd_list(message: Message) -> None:
    """Показать запросы пользователя."""
    user_requests = load_user_requests(message.from_user.id)
    response = format_user_requests_list(user_requests)

    await message.answer(response, reply_markup=get_back_menu_keyboard())


@dp.message(F.text.len() > 0)
async def handle_text(message: Message, state: FSMContext) -> None:
    """Обработка текстовых сообщений."""
    text = message.text.strip()
    user = message.from_user

    # Разбираем сообщение
    parts = text.split()
    keywords = []
    channels = []

    for part in parts:
        if part.startswith('@') or part.startswith('https://t.me/') or 't.me/' in part:
            channels.append(part)
        else:
            keywords.append(part)

    # Валидируем входные данные
    keywords = validate_keywords(keywords)
    channels = validate_channels(channels)

    # Проверяем валидность данных
    if not keywords and not channels:
        await message.answer(
            "❌ <b>Некорректный запрос</b>\n\n"
            "Не удалось распознать ни ключевые слова, ни каналы.\n\n"
            "Используй формат:\n"
            "<code>ключевые слова @канал1 @канал2</code>\n\n"
            "Примеры:\n"
            "• <code>python разработка @python</code>\n"
            "• <code>машинное обучение @ml @datascience</code>"
        )
        return

    if not keywords:
        await message.answer(
            "❌ <b>Не указаны ключевые слова</b>\n\n"
            "Пожалуйста, укажите слова для поиска.\n\n"
            "Примеры:\n"
            "• <code>python django flask</code>\n"
            "• <code>машинное обучение AI</code>"
        )
        return

    if not channels:
        # Проверяем, не слишком ли много ключевых слов для пошагового режима
        if len(keywords) > 3:
            await message.answer(
                "❌ <b>Не указаны каналы</b>\n\n"
                f"🔍 Ключевые слова: {', '.join(keywords)}\n\n"
                "Укажите каналы для поиска:\n"
                "<code>@channel1 @channel2 https://t.me/channel3</code>\n\n"
                "Или отправьте ключевые слова отдельно, и я спрошу каналы."
            )
            return

        # Пошаговый режим
        await state.update_data(keywords=keywords)
        await message.answer(
            f"📝 Ключевые слова: {', '.join(keywords)}\n\n"
            "Теперь укажи каналы для поиска:\n"
            "<code>@channel1 @channel2 https://t.me/channel3</code>\n\n"
            "Поддерживаемые форматы:\n"
            "• <code>@username</code>\n"
            "• <code>https://t.me/channel</code>\n"
            "• <code>t.me/channel</code>"
        )
        await state.set_state(SearchForm.channels)
        return

    # Проверяем лимиты
    if len(keywords) > 10:
        await message.answer(
            f"⚠️ <b>Слишком много ключевых слов</b>\n\n"
            f"Указано: {len(keywords)}, максимум: 10\n\n"
            f"Будут использованы первые 10: {', '.join(keywords[:10])}"
        )
        keywords = keywords[:10]

    if len(channels) > 5:
        await message.answer(
            f"⚠️ <b>Слишком много каналов</b>\n\n"
            f"Указано: {len(channels)}, максимум: 5\n\n"
            f"Будут использованы первые 5: {', '.join(channels[:5])}"
        )
        channels = channels[:5]

    # Сохраняем запрос
    request = SearchRequest(
        user_id=user.id,
        username=user.username,
        keywords=keywords,
        channels=channels,
        created_at=datetime.now().isoformat()
    )

    save_request(request)

    # Создаем клавиатуру для сохраненного запроса
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить поиск", callback_data="execute_search")
    builder.button(text="🏠 Главное меню", callback_data="back_to_menu")
    markup = builder.as_markup()

    await message.answer(
        "✅ <b>Запрос сохранен!</b>\n\n"
        f"🔍 Ключевые слова ({len(keywords)}): {', '.join(keywords)}\n"
        f"📺 Каналы ({len(channels)}): {', '.join(channels)}\n\n"
        "Результаты поиска будут обработаны позже.",
        reply_markup=markup
    )
    await state.clear()


@dp.message(SearchForm.channels, F.text.len() > 0)
async def handle_channels_only(message: Message, state: FSMContext) -> None:
    """Обработка каналов в пошаговом режиме."""
    channels = validate_channels(normalize_list(message.text))
    if not channels:
        await message.answer(
            "❌ <b>Не удалось распознать каналы</b>\n\n"
            "Пожалуйста, укажите каналы в правильном формате:\n"
            "<code>@channel1 @channel2 https://t.me/channel3</code>\n\n"
            "Поддерживаемые форматы:\n"
            "• <code>@username</code>\n"
            "• <code>https://t.me/channel</code>\n"
            "• <code>t.me/channel</code>\n"
            "• <code>username</code> (будет преобразовано в @username)"
        )
        return

    data = await state.get_data()
    keywords = data.get("keywords", [])

    if len(channels) > 5:
        await message.answer(
            f"⚠️ <b>Слишком много каналов</b>\n\n"
            f"Указано: {len(channels)}, максимум: 5\n\n"
            f"Будут использованы первые 5: {', '.join(channels[:5])}"
        )
        channels = channels[:5]

    request = SearchRequest(
        user_id=message.from_user.id,
        username=message.from_user.username,
        keywords=keywords,
        channels=channels,
        created_at=datetime.now().isoformat()
    )

    save_request(request)

    # Создаем клавиатуру для сохраненного запроса
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить поиск", callback_data="execute_search")
    builder.button(text="🏠 Главное меню", callback_data="back_to_menu")
    markup = builder.as_markup()

    await message.answer(
        "✅ <b>Запрос сохранен!</b>\n\n"
        f"🔍 Ключевые слова ({len(keywords)}): {', '.join(keywords)}\n"
        f"📺 Каналы ({len(channels)}): {', '.join(channels)}\n\n"
        "Результаты поиска будут обработаны позже.",
        reply_markup=markup
    )
    await state.clear()


@dp.message(SearchForm.keywords, F.text.len() > 0)
async def handle_keywords_only(message: Message, state: FSMContext) -> None:
    """Обработка ключевых слов в пошаговом режиме."""
    keywords = validate_keywords(normalize_list(message.text))
    if not keywords:
        await message.answer(
            "❌ <b>Не удалось распознать ключевые слова</b>\n\n"
            "Пожалуйста, укажите слова для поиска.\n"
            "Каждое слово должно содержать минимум 2 символа.\n\n"
            "Примеры:\n"
            "• <code>python django flask</code>\n"
            "• <code>машинное обучение AI</code>\n"
            "• <code>разработка, программирование, код</code>"
        )
        return

    data = await state.get_data()
    channels = data.get("channels", [])

    if len(keywords) > 10:
        await message.answer(
            f"⚠️ <b>Слишком много ключевых слов</b>\n\n"
            f"Указано: {len(keywords)}, максимум: 10\n\n"
            f"Будут использованы первые 10: {', '.join(keywords[:10])}"
        )
        keywords = keywords[:10]

    request = SearchRequest(
        user_id=message.from_user.id,
        username=message.from_user.username,
        keywords=keywords,
        channels=channels,
        created_at=datetime.now().isoformat()
    )

    save_request(request)

    # Создаем клавиатуру для сохраненного запроса
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить поиск", callback_data="execute_search")
    builder.button(text="🏠 Главное меню", callback_data="back_to_menu")
    markup = builder.as_markup()

    await message.answer(
        "✅ <b>Запрос сохранен!</b>\n\n"
        f"🔍 Ключевые слова ({len(keywords)}): {', '.join(keywords)}\n"
        f"📺 Каналы ({len(channels)}): {', '.join(channels)}\n\n"
        "Результаты поиска будут обработаны позже.",
        reply_markup=markup
    )
    await state.clear()


async def main() -> None:
    """Запуск бота."""
    if TELETHON_AVAILABLE:
        logger.info("Запуск бота для парсинга Telegram каналов с Telethon...")
    else:
        logger.info("Запуск бота (Telethon не доступен - только сбор запросов)")

    # Инициализируем Telethon клиент
    if TELETHON_AVAILABLE and telethon_client:
        try:
            await telethon_client.connect()
            logger.info("Telethon клиент подключен")
        except Exception as e:
            logger.warning(f"Не удалось подключить Telethon клиент: {e}")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if TELETHON_AVAILABLE and telethon_client:
            try:
                await telethon_client.disconnect()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())
