from aiogram import Bot, Dispatcher
import asyncio
import asyncpg
from app.handlers import router
from database.module import DATABASE_URL
from data_x import TOKEN
from aiogram.fsm.storage.memory import MemoryStorage

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

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
    #await create_table()  # Создание таблицы (если нужно)
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
