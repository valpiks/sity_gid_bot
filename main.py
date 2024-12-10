from aiogram import Bot, Dispatcher
import asyncio
import asyncpg
from app.handlers import router 
from database.module import DATABASE_URL

dp = Dispatcher()

TOKEN = "7918689800:AAE5_tyQAg8EyH8l-0UGz-huHz42pI1_0WE"
bot = Bot(token=TOKEN)

async def send_notifications():
    while True:
        conn = await asyncpg.connect(DATABASE_URL)
        subscribers = await conn.fetch("SELECT user_id FROM users WHERE subscribed = TRUE")
        await conn.close()
        for subscriber in subscribers:
            user_id = subscriber['user_id']
            try:
                await bot.send_message(user_id, "Новые тренды и акции в Ростове-на-Дону!")
            except Exception as e:
                print(f"Ошибка отправки уведомления пользователю {user_id}: {e}")
        await asyncio.sleep(3600)


async def main():
	dp.include_router(router)
	await dp.start_polling(bot)


if __name__ == '__main__':
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		print("Exit")