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

router = Router()


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


@router.message(F.text == "Построить маршрут")
async def build_route(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()

    if not user or user['latitude'] is None or user['longitude'] is None:
        await message.answer("Пожалуйста, сначала отправьте вашу геолокацию.")
        return

    user_latitude = user['latitude']
    user_longitude = user['longitude']
    destination_latitude = 47.222078
    destination_longitude = 39.720349

    route_url = f"https://api.openrouteservice.org/v2/directions/driving-car/geojson"
    headers = {
        "Authorization": OPENROUTESERVICE_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "coordinates": [
            [user_longitude, user_latitude],
            [destination_longitude, destination_latitude]
        ]
    }

    try:
        response = requests.post(route_url, headers=headers, json=data)
        response.raise_for_status()
        route_data = response.json()

        if route_data.get("features"):
            route = route_data["features"][0]["properties"]
            duration = route["summary"]["duration"]
            distance = route["summary"]["distance"]
            duration_minutes = duration / 60
            distance_km = distance / 1000
            map_url = f"https://www.openstreetmap.org/directions?engine=osrm_car&route={user_latitude},{user_longitude}-{destination_latitude},{destination_longitude}"

            await message.answer(f"Маршрут построен:\n"
                                 f"Расстояние: {distance_km:.2f} км\n"
                                 f"Время в пути: {duration_minutes:.2f} мин\n"
                                 f"Ссылка на карту: {map_url}")
        else:
            await message.answer("Не удалось построить маршрут. Попробуйте позже.")
    except requests.exceptions.RequestException as e:
        await message.answer(f"Ошибка при построении маршрута: {e}")


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