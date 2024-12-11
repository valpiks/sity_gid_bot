import app.keyboard as kb
from database.module import DATABASE_URL
import requests
import g4f
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import asyncpg
from app.URL import OPENROUTESERVICE_API_KEY, API_KEY
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bs4 import BeautifulSoup
import folium
router = Router()
import json

# Функция для парсинга данных с 2ГИС
def parse_2gis(query, city="Ростов-на-Дону"):
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": query,  # Поисковый запрос
        "city": city,  # Город
        "key": API_KEY,  # API-ключ
        "page_size": 10  # Количество результатов на странице
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Пример парсинга (зависит от структуры страницы)
        places = []
        for item in soup.find_all("div", class_="_1tfwnxl"):
            name = item.find("h1", class_="_cwjbox").text.strip()
            address = item.find("span", class_="_er2xx9").text.strip()
            rating = item.find("div", class_="_y10azs")
            rating = float(rating.text.strip()) if rating else 0.0
            places.append({
                "name": name,
                "address": address,
                "rating": rating
            })

        return places
    except Exception as e:
        print(f"Ошибка при парсинге 2ГИС: {e}")
        return []


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, subscribed) VALUES ($1, $2)", user_id, False)
    await conn.close()
    await message.answer("Привет! Я бот-гид для Ростова-на-Дону. Для подборки ближайших мест интересных тебе нужно отправить мне геолокацию. Чем могу помочь?", reply_markup=kb.main)


@router.message(Command("subscribe"))
async def subscribe(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET subscribed = TRUE WHERE user_id = $1", user_id)
    await conn.close()
    await message.answer("Вы подписались на уведомления о новых трендах, скидках и популярных местах!")


@router.message(Command("unsubscribe"))
async def unsubscribe(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET subscribed = FALSE WHERE user_id = $1", user_id)
    await conn.close()
    await message.answer("Вы отписались от уведомлений.")


@router.message(F.location)
async def handle_location(message: Message):
    latitude = message.location.latitude
    longitude = message.location.longitude

    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET latitude = $1, longitude = $2 WHERE user_id = $3", latitude, longitude, user_id)
    await conn.close()
    await message.answer("Ваша геолокация сохранена.")


# Функция для построения маршрута по дороге через API 2ГИС
def build_route_2gis(start_lat, start_lon, end_lat, end_lon):
    url = "https://routing.api.2gis.com/carrouting/6.0.0/global"
    params = {
        "key": API_KEY,
        "version": "1.0",
        "locale": "ru",
        "points": f"[{start_lon},{start_lat},{end_lon},{end_lat}]",
        "type": "jam"  # Тип маршрута (с учетом пробок)
    }

    try:
        response = requests.get(url, params=params)  # Используем GET-запрос
        print("URL:", response.url)  # Вывод URL для отладки
        print("Params:", params)  # Вывод параметров для отладки
        response.raise_for_status()
        data = response.json()

        if data.get("result"):
            route = data["result"][0]
            duration = route["total_time"]  # Время в секундах
            distance = route["total_distance"]  # Расстояние в метрах
            return duration, distance, route["geometry"]  # Возвращаем геометрию маршрута
        else:
            return None, None, None
    except Exception as e:
        print(f"Ошибка при построении маршрута через API 2ГИС: {e}")
        print("Response:", response.text)  # Вывод ответа для отладки
        return None, None, None


@router.message(F.text == "Составить маршрут")
async def build_route(message: Message):
    user_id = message.from_user.id

    # Получение координат пользователя из базы данных
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT latitude, longitude FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if not user or user['latitude'] is None or user['longitude'] is None:
        await message.answer("Пожалуйста, сначала отправьте вашу геолокацию.")
        return

    # Координаты пользователя
    start_lat, start_lon = user['latitude'], user['longitude']

    # Конечная точка (например, Ростовский кремль)
    end_lat, end_lon = 47.222078, 39.720349

    # Построение маршрута
    duration, distance, geometry = build_route_2gis(start_lat, start_lon, end_lat, end_lon)

    if duration and distance:
        await message.answer(f"Маршрут построен:\n"
                             f"Расстояние: {distance / 1000:.2f} км\n"
                             f"Время в пути: {duration / 60:.2f} мин")
    else:
        await message.answer("Не удалось построить маршрут.")


class PreferencesForm(StatesGroup):
    waiting_for_preferences = State()


@router.message(F.text == "Указать предпочтения")
async def set_preferences(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, напиши свои предпочтения (например, 'люблю музеи, рестораны, природу').")
    await state.set_state(PreferencesForm.waiting_for_preferences)


@router.message(F.text, PreferencesForm.waiting_for_preferences)
async def save_preferences(message: Message, state: FSMContext):
    user_id = message.from_user.id
    preferences = message.text

    try:
        prompt = f"Определи типы мест из текста: '{preferences}'. Ответь кратко, перечисли типы мест через запятую. Исключай другие слова кроме типов мест."
        response = g4f.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
        )
        ai_preferences = response.strip()

        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("UPDATE users SET preferences = $1 WHERE user_id = $2", ai_preferences, user_id)
        await conn.close()

        await message.answer(f"Ваши предпочтения сохранены: {ai_preferences}")
    except Exception as e:
        await message.answer(f"Ошибка при обработке предпочтений: {e}")

    await state.clear()


@router.message()
async def handle_text(message: Message):
    query = message.text
    user_id = message.from_user.id

    # Получаем предпочтения пользователя из базы данных
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT preferences FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if not user or not user['preferences']:
        await message.answer("Пожалуйста, сначала укажите свои предпочтения.")
        return

    preferences = user['preferences']

    # Парсинг данных с 2ГИС
    places = parse_2gis(query)

    # Фильтрация по рейтингу (например, рейтинг >= 4.0)
    filtered_places = [place for place in places if place["rating"] >= 4.0]

    # Фильтрация по предпочтениям
    filtered_by_preferences = []
    for place in filtered_places:
        if any(pref.lower() in place["name"].lower() for pref in preferences.split(", ")):
            filtered_by_preferences.append(place)

    if filtered_by_preferences:
        response = "Найденные места по вашему запросу и предпочтениям:\n"
        for idx, place in enumerate(filtered_by_preferences, start=1):
            response += f"{idx}. {place['name']} - {place['address']} (Рейтинг: {place['rating']})\n"
        await message.answer(response)
    else:
        await message.answer("По вашему запросу и предпочтениям ничего не найдено.")