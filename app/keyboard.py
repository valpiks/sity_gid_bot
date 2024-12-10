from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)

from aiogram.utils.keyboard import InlineKeyboardBuilder


main = ReplyKeyboardMarkup(keyboard=
[
	[KeyboardButton(text="Указать предпочтения"),
	KeyboardButton(text="Скидки и акции")],
	[KeyboardButton(text="Отправить геолокацию", request_location=True),
	KeyboardButton(text="Настройки")],
	[KeyboardButton(text="Подписаться на уведомления"),
	KeyboardButton(text="Отписаться от уведомлений")],
	[KeyboardButton(text=""),
  KeyboardButton(text="Построить маршрут")]
],
	resize_keyboard=True)

notice = InlineKeyboardMarkup(inline_keyboard=[
		[InlineKeyboardButton(text="Подписаться на уведомления")],
		[InlineKeyboardButton(text="Отписаться от уведомления")]
	]
)


start = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text="Начнём настройку")]],
	resize_keyboard=True,
	one_time_keyboard=True)





