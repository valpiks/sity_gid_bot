from aiogram import Bot, Dispatcher, types 
import asyncio
from aiogram.filters import Command
from app.handlers import router
from data_x import TOKEN
from bs4 import BeautifulSoup
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import requests
import logging
import asyncpg
from database.module import DATABASE_URL

# Настройка логирования
logging.basicConfig(level=logging.INFO)


# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

scheduler = AsyncIOScheduler()
AFISHA_URL = "https://afisha.yandex.ru/rostov-na-donu"

# Функция для парсинга расписания мероприятий
def get_events():
    try:
        response = requests.get(AFISHA_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Пример парсинга (вам нужно адаптировать под структуру сайта)
        events = []
        for event in soup.find_all("div", class_="event-item"):
            title = event.find("h2").text.strip()
            date = event.find("span", class_="date").text.strip()
            location = event.find("span", class_="location").text.strip()
            events.append(f"📅 {date} - {title}\n📍 {location}")

        return "\n\n".join(events) if events else "Мероприятия не найдены."
    except Exception as e:
        logging.error(f"Ошибка при парсинге сайта: {e}")
        return "Не удалось получить данные о мероприятиях."


# Команда /subscribe для подписки на уведомления
@router.message(Command("subscribe"))
async def subscribe(message: types.Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Проверяем, подписан ли пользователь уже
        existing_subscription = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if existing_subscription and existing_subscription["subscribed"]:
            await message.answer("Вы уже подписаны на уведомления!")
        else:
            # Добавляем или обновляем пользователя в базе данных
            await conn.execute("""
                INSERT INTO users (user_id, subscribed) VALUES ($1, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET subscribed = TRUE
            """, user_id)
            await message.answer("Вы успешно подписались на уведомления о новых мероприятиях!")
    finally:
        await conn.close()


# Команда /unsubscribe для отписки от уведомлений
@router.message(Command("unsubscribe"))
async def unsubscribe(message: types.Message):
    user_id = message.from_user.id
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # Проверяем, подписан ли пользователь
        existing_subscription = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
        if existing_subscription and existing_subscription["subscribed"]:
            # Обновляем статус подписки
            await conn.execute("UPDATE users SET subscribed = FALSE WHERE user_id = $1", user_id)
            await message.answer("Вы успешно отписались от уведомлений.")
        else:
            await message.answer("Вы не подписаны на уведомления.")
    finally:
        await conn.close()


# Команда /schedule для получения расписания мероприятий
@router.message(Command("schedule"))
async def get_schedule(message: types.Message):
    schedule = get_events()
    await message.answer(f"📅 Расписание мероприятий:\n\n{schedule}")


# Функция для отправки уведомлений о ближайших мероприятиях
async def send_notifications():
    while True:
        schedule = get_events()
        if schedule:
            conn = await asyncpg.connect(DATABASE_URL)
            try:
                # Получаем список подписанных пользователей
                subscribed_users = await conn.fetch("SELECT user_id FROM users WHERE subscribed = TRUE")
                for user in subscribed_users:
                    await bot.send_message(user["user_id"], f"🔔 Ближайшие мероприятия:\n\n{schedule}")
            finally:
                await conn.close()
        await asyncio.sleep(3600)  # Отправка уведомлений каждый час



async def main():
    # Создаем таблицы в базе данных
    #await create_tables()

    # Регистрируем роутер (если есть)
    dp.include_router(router)

    # Запускаем отправку уведомлений
    asyncio.create_task(send_notifications())

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())