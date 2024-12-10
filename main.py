from aiogram import Bot, Dispatcher
import asyncio
from app.handlers import router 
from database.module import cursor
dp = Dispatcher()

TOKEN = "8098734676:AAFSKLAzyDZ2sl78vYsblrBq08JQYHWEmuo"
bot = Bot(token=TOKEN)

async def send_notifications():
    while True:
        cursor.execute("SELECT user_id FROM users WHERE subscribed = 1")
        subscribers = cursor.fetchall()
        for subscriber in subscribers:
            user_id = subscriber[0]
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