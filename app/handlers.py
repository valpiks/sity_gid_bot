from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
import asyncpg
import app.keyboard as kb
from database.module import DATABASE_URL
import openai
import requests


router = Router()

YANDEX_MAPS_API_KEY = "a6e233d2-92d2-4db9-a6a7-34a7313d672e"
openai.api_key = "sk-mnopqrstuvwxabcdmnopqrstuvwxabcdmnopqrst"



@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, subscribed) VALUES ($1, $2)", user_id, False)
    await conn.close()
    await message.answer("Привет! Я бот-гид для Ростова-на-Дону. Для подборки ближайших мест инетерсных тебе нужно отправить мне геолокацию. Чем могу помочь?", reply_markup= kb.main)


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

# Обработчик указания предпочтений
@router.message(F.text == "Указать предпочтения")
async def set_preferences(message: Message):
    await message.answer("Пожалуйста, напишите ваши предпочтения (например, 'люблю музеи и рестораны').")

# Обработчик текстовых сообщений для сохранения предпочтений
@router.message(F.text)
async def save_preferences(message: Message):
    user_id = message.from_user.id
    preferences = message.text

    # Анализируем предпочтения с помощью OpenAI
    ai_response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Определи типы мест из текста: {preferences}",
        max_tokens=50
    )
    ai_preferences = ai_response.choices[0].text.strip()

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


# Обработчик построения маршрута
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