from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import asyncio
import asyncpg
from app.handlers import router
from database.module import DATABASE_URL, create_table
import httpx

# Настройки прокси
PROXY_AUTH = httpx.BasicAuth("username", "password")
PROXY_URL = "http://207.246.87.152:11201"

# Токен бота
TOKEN = "7918689800:AAE5_tyQAg8EyH8l-0UGz-huHz42pI1_0WE"
# Инициализация бота и диспетчера
bot = Bot(token=TOKEN, proxy=PROXY_URL, proxy_auth=PROXY_AUTH, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Функция для отправки уведомлений
async def send_notifications():
    while True:
        conn = await asyncpg.connect(DATABASE_URL)
        subscribers = await conn.fetch("SELECT user_id FROM users WHERE subscribed = TRUE")
        await conn.close()
        for subscriber in subscribers:
            user_id = subscriber['user_id']
            try:
                await bot.send_message(chat_id=user_id, text="Новые тренды и акции в Ростове-на-Дону!")
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        await asyncio.sleep(3600)  # Отправка уведомлений раз в час

# Основная функция
async def main():
    await create_table()  # Создание таблицы (если нужно)
    # Регистрация роутера (если есть)
    dp.include_router(router)
    # Запуск диспетчера
    await dp.start_polling(bot)

    # Запуск отправки уведомлений
    asyncio.create_task(send_notifications())

if __name__ == '__main__':  # Исправлена ошибка с пропущенными подчеркиваниями
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")
