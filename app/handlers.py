import app.keyboard as kb
from database.module import DATABASE_URL
import openai
import requests
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart
import asyncpg
import asyncio

router = Router()

YANDEX_MAPS_API_KEY = "a6e233d2-92d2-4db9-a6a7-34a7313d672e"

openai.api_key = "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"

API_URL = f"https://search-maps.yandex.ru/v1/?text=популярные места Ростов-на-Дону&lang=ru_RU&apikey={YANDEX_MAPS_API_KEY}"

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, subscribed) VALUES ($1, $2)", user_id, False)
    await conn.close()
    await message.answer("Привет! Я бот-гид для Ростова-на-Дону. Для подборки ближайших мест инетерсных тебе нужно отправить мне геолокацию. Чем могу помочь?", reply_markup=kb.main)

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
    preferences = await conn.fetchval("SELECT preferences FROM users WHERE user_id = $1", user_id)
    await conn.close()

# Функция для обновления данных из API
async def update_data():
    while True:
        try:
            # Запрос к API
            response = requests.get(API_URL)
            data = response.json()

            # Сохранение данных в базу данных
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute("DELETE FROM events")  # Очищаем таблицу перед обновлением
            for event in data.get("features", []):  # Исправлено: обрабатываем "features"
                title = event["properties"]["name"]
                description = event["properties"].get("description", "Нет описания")
                await conn.execute("""
                INSERT INTO events (type, title, description) VALUES ($1, $2, $3)
                """, "place", title, description)
            await conn.close()

            print("Данные обновлены")
        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")

        # Обновление данных каждые 60 минут
        await asyncio.sleep(3600)

# Обработчик запроса популярных мест
@router.message(F.text == "Популярные места в Ростове")
async def popular_places(message: Message):
    conn = await asyncpg.connect(DATABASE_URL)
    places = await conn.fetch("SELECT title, description FROM events WHERE type = 'place'")
    await conn.close()

    if places:
        response = "Популярные места в Ростове:\n"
        for idx, place in enumerate(places, start=1):
            response += f"{idx}. {place['title']} - {place['description']}\n"
        await message.answer(response)
    else:
        await message.answer("Нет данных о популярных местах.")

# Обработчик запроса скидок и акций
@router.message(F.text == "Скидки и акции")
async def discounts(message: Message):
    conn = await asyncpg.connect(DATABASE_URL)
    discounts = await conn.fetch("SELECT title, description FROM events WHERE type = 'discount'")
    await conn.close()

    if discounts:
        response = "Скидки и акции в Ростове:\n"
        for idx, discount in enumerate(discounts, start=1):
            response += f"{idx}. {discount['title']} - {discount['description']}\n"
        await message.answer(response)
    else:
        await message.answer("Нет данных о скидках и акциях.")

# Обработчик указания предпочтений
@router.message(F.text == "Указать предпочтения")
async def set_preferences(message: Message):
    await message.answer("Пожалуйста, напишите ваши предпочтения (например, 'люблю музеи и рестораны').")

# Обработчик текстовых сообщений для сохранения предпочтений
@router.message(F.text)
async def save_preferences(message: Message):
    user_id = message.from_user.id
    preferences = message.text

    # Анализируем предпочтения с помощью OpenAI (используем gpt-3.5-turbo)
    ai_response = openai.ChatCompletion.create(
        model="gpt-4",  # Используем современную модель
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"Определи типы мест из текста: {preferences}"}
        ],
        max_tokens=50
    )
    ai_preferences = ai_response.choices[0].message.content.strip()

    # Сохраняем предпочтения в базе данных
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("UPDATE users SET preferences = $1 WHERE user_id = $2", ai_preferences, user_id)
    await conn.close()

    await message.answer(f"Ваши предпочтения сохранены: {ai_preferences}")

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

    # Построение маршрута с помощью Яндекс.Карт API
    route_url = f"https://api.routing.yandex.net/v2/route?waypoints={user_latitude},{user_longitude}|{destination_latitude},{destination_longitude}&apikey={YANDEX_MAPS_API_KEY}"
    response = requests.get(route_url)
    data = response.json()

    if data.get("routes"):
        route = data["routes"][0]
        duration = route["duration"]  # Время в пути в секундах
        distance = route["distance"]  # Расстояние в метрах

        # Формируем ссылку на карту с маршрутом
        map_url = f"https://yandex.ru/maps/?rtext={user_latitude},{user_longitude}~{destination_latitude},{destination_longitude}&rtt=auto"

        await message.answer(f"Маршрут построен:\n"
                             f"Расстояние: {distance / 1000:.2f} км\n"
                             f"Время в пути: {duration // 60} мин\n"
                             f"Ссылка на карту: {map_url}")
    else:
        await message.answer("Не удалось построить маршрут. Попробуйте позже.")