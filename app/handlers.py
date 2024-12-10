from aiogram import F, Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

import app.keyboard as kb
from database.module import cursor, conn

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, subscribed) VALUES (?, ?)", (user_id, 0))
        conn.commit()
    await message.answer("Привет! Я бот-гид для Ростова-на-Дону. Чем могу помочь?", reply_markup= kb.start)



@router.message(F.text == "Подписаться на уведомления")
async def subscribe(message: Message):
    user_id = message.from_user.id
    cursor.execute("UPDATE users SET subscribed = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    await message.answer("Вы подписались на уведомления о новых трендах, скидках и популярных местах!")

@router.message(F.text == "Отписаться от уведомлений")
async def unsubscribe(message: Message):
    user_id = message.from_user.id
    cursor.execute("UPDATE users SET subscribed = 0 WHERE user_id = ?", (user_id,))
    conn.commit()
    await message.answer("Вы отписались от уведомлений.")


@router.message(F.text == 'Начнём настройку' or "Настройки")
async def district(message: Message):
  await message.answer('Отправте вашу геолокацию', reply_markup= kb.district)


@router.message(F.location)
async def handle_location(message: Message):
	await message.answer("Напишите ваши предпочтения(Театр, кино, парки, достопримечательности и т.п.)")


@router.message(F.text == "")
async def idea(message: Message):
	await message.answer("Настройка завершенна, на основе ваших предпочтений было подобранно несколько мест, которые могут вам понравится, хотите ознакомиться?")


@router.message(Command("id"))
async def cmd_id(message: Message):
	await message.answer(f"Ваш id: {message.from_user.id}")