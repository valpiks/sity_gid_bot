import app.keyboard as kb
from database.module import DATABASE_URL
import requests
import g4f
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import asyncpg
from app.URL import OPENROUTESERVICE_API_KEY, FOURSQUARE_API_KEY
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import os
import folium
import requests
from folium.plugins import MarkerCluster
import asyncio


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, subscribed) VALUES ($1, $2)", user_id, False)
    await conn.close()
    await message.answer("Привет! Я бот-гид для Ростова-на-Дону. Для подборки ближайших мест интересных тебе нужно отправить мне геолокацию. Чем могу помочь?", reply_markup=kb.main)




@router.message(F.text == "Подписаться на уведомления")
async def subscribe(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET subscribed = TRUE WHERE user_id = $1", user_id)
    await conn.close()
    await message.answer("Вы подписались на уведомления о новых трендах, скидках и популярных местах!")




@router.message(F.text == "Отписаться от уведомлений")
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

    # Получаем координаты пользователя
    user_latitude = user['latitude']
    user_longitude = user['longitude']

    # Пример места назначения (например, Ростовский кремль)
    destination_latitude = 47.222078
    destination_longitude = 39.720349

    # Построение маршрута с помощью OpenRouteService API
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
            duration = route["summary"]["duration"]  # Время в секундах
            distance = route["summary"]["distance"]  # Расстояние в метрах

            # Преобразование времени в минуты и расстояния в километры
            duration_minutes = duration / 60
            distance_km = distance / 1000

            # Формируем ссылку на карту с маршрутом
            map_url = f"https://www.openstreetmap.org/directions?engine=osrm_car&route={user_latitude},{user_longitude}-{destination_latitude},{destination_longitude}"

            await message.answer(f"Маршрут построен:\n"
                                 f"Расстояние: {distance_km:.2f} км\n"
                                 f"Время в пути: {duration_minutes:.2f} мин\n"
                                 f"Ссылка на карту: {map_url}")
        else:
            await message.answer("Не удалось построить маршрут. Попробуйте позже.")
    except requests.exceptions.RequestException as e:
        await message.answer(f"Ошибка при построении маршрута: {e}")




# Обработчик запроса популярных мест
@router.message(F.text == "Популярные места в Ростове")
async def popular_places(message: Message):
    user_id = message.from_user.id

    # Подключаемся к базе данных
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT latitude, longitude FROM users WHERE user_id = $1", user_id)
    await conn.close()

    # Проверяем, есть ли у пользователя сохраненная геолокация
    if not user or user['latitude'] is None or user['longitude'] is None:
        await message.answer("Пожалуйста, сначала отправьте вашу геолокацию.")
        return

    # Координаты пользователя
    user_latitude = user['latitude']
    user_longitude = user['longitude']
    center_location = f"{user_latitude},{user_longitude}"

    # Запрос к Foursquare API
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY  # Ваш API ключ Foursquare
    }
    params = {
        "ll": center_location,  # Координаты пользователя
        "radius": 5000,  # Радиус поиска в метрах
        "limit": 10,  # Количество мест
        "categories": "13000"  # Категория "Еда и напитки" (можно изменить на нужную)
    }

    try:
        # Выполняем запрос к Foursquare API
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()

        # Обрабатываем результаты
        if data.get("results"):
            response_text = "Популярные места рядом с вами:\n"
            for idx, place in enumerate(data["results"], start=1):
                name = place.get("name", "Неизвестное место")
                address = place.get("location", {}).get("address", "Адрес не указан")
                rating = place.get("rating", "Нет рейтинга")
                response_text += f"{idx}. {name} - {address} (Рейтинг: {rating})\n"
            await message.answer(response_text)
        else:
            await message.answer("Нет данных о популярных местах рядом с вами.")

    except requests.exceptions.RequestException as e:
        await message.answer(f"Ошибка при запросе к Foursquare API: {e}")



# Обработчик запроса скидок и акций
@router.message(F.text == "Скидки и акции")
async def discounts(message: Message):
    user_id = message.from_user.id

    # Подключаемся к базе данных
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT latitude, longitude FROM users WHERE user_id = $1", user_id)
    await conn.close()

    # Проверяем, есть ли у пользователя сохраненная геолокация
    if not user or user['latitude'] is None or user['longitude'] is None:
        await message.answer("Пожалуйста, сначала отправьте вашу геолокацию.")
        return

    # Координаты пользователя
    user_latitude = user['latitude']
    user_longitude = user['longitude']
    center_location = f"{user_latitude},{user_longitude}"

    # Запрос к Foursquare API для поиска скидок и акций
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY  # Ваш API ключ Foursquare
    }
    params = {
        "ll": center_location,  # Координаты пользователя
        "radius": 5000,  # Радиус поиска в метрах
        "limit": 10,  # Количество мест
        "query": "discount"  # Ключевое слово для поиска скидок
    }

    try:
        # Выполняем запрос к Foursquare API
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()  # Проверяем статус ответа
        data = response.json()

        # Обрабатываем результаты
        if data.get("results"):
            response_text = "Скидки и акции рядом с вами:\n"
            for idx, place in enumerate(data["results"], start=1):
                name = place.get("name", "Неизвестное место")
                address = place.get("location", {}).get("address", "Адрес не указан")
                discount_info = place.get("description", "Нет информации о скидке")
                response_text += f"{idx}. {name} - {address} ({discount_info})\n"
            await message.answer(response_text)
        else:
            await message.answer("Нет данных о скидках и акциях рядом с вами.")

    except requests.exceptions.RequestException as e:
        await message.answer(f"Ошибка при запросе к Foursquare API: {e}")


class PreferencesForm(StatesGroup):
    waiting_for_preferences = State() 


@router.message(F.text == "Указать предпочтения")
async def set_preferences(message: Message, state: FSMContext):
    await message.answer("Пожалуйста, напишите ваши предпочтения (например, 'люблю музеи и рестораны').")
    await state.set_state(PreferencesForm.waiting_for_preferences)  # Переходим в состояние ожидания



# Обработчик текстовых сообщений для сохранения предпочтений
@router.message(F.text, PreferencesForm.waiting_for_preferences)
async def save_preferences(message: Message, state: FSMContext):
    user_id = message.from_user.id
    preferences = message.text

    # Анализируем предпочтения с помощью g4f
    try:
        # Формируем запрос для g4f
        prompt = f"Определи типы мест из текста: '{preferences}'. Ответь кратко, перечисли типы мест через запятую. Исключай другие слова кроме типов мест."
        response = g4f.ChatCompletion.create(
            model="gpt-4",  # Используем современную модель
            messages=[{"role": "user", "content": prompt}],
        )
        ai_preferences = response.strip()  # Получаем ответ от модели

        # Сохраняем предпочтения в базе данных
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("UPDATE users SET preferences = $1 WHERE user_id = $2", ai_preferences, user_id)
        await conn.close()

        await message.answer(f"Ваши предпочтения сохранены: {ai_preferences}")
    except Exception as e:
        await message.answer(f"Ошибка при обработке предпочтений: {e}")

    # Завершаем состояние
    await state.clear()

# Функция для получения мест с рейтингом (Foursquare API)
def get_places_with_rating(location, radius=5000, limit=10):
    url = "https://api.foursquare.com/v3/places/search"
    headers = {
        "Accept": "application/json",
        "Authorization": FOURSQUARE_API_KEY
    }
    params = {
        "ll": f"{location[0]},{location[1]}",  # Координаты
        "radius": radius,  # Радиус поиска в метрах
        "limit": limit  # Количество мест
    }
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()  # Проверяем статус ответа
    data = response.json()

    # Извлекаем места с рейтингом
    places = []
    for place in data.get("results", []):
        name = place.get("name")
        location = place.get("geocodes", {}).get("main", {})
        latitude = location.get("latitude")
        longitude = location.get("longitude")
        rating = place.get("rating", 0)  # Рейтинг (если доступен)
        if latitude and longitude:
            places.append({
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "rating": rating
            })
    return places




@router.message(F.text)
async def ignore_messages(message: Message):
    await message.answer("Я вас не понимаю. Пожалуйста, используйте доступные команды.")
