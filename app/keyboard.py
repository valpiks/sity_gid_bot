from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           )

from aiogram.utils.keyboard import InlineKeyboardBuilder


main = ReplyKeyboardMarkup(keyboard=
[
	[KeyboardButton(text="Популярные места в Ростове"),
	KeyboardButton(text="Указать предпочтения")],
	[KeyboardButton(text="Отправить геолокацию", request_location=True),
  KeyboardButton(text="Составить маршрут")]
],
	resize_keyboard=True)



start = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text="Начнём настройку")]],
	resize_keyboard=True,
	one_time_keyboard=True)





