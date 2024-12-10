from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton)

from aiogram.utils.keyboard import InlineKeyboardBuilder


main = ReplyKeyboardMarkup(keyboard=
[
	[KeyboardButton(text="Локации"),
	KeyboardButton(text="Акции")],
	[KeyboardButton(text="Уведомления"),
	KeyboardButton(text="Настройки")]
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


district = ReplyKeyboardMarkup(keyboard=[
	[KeyboardButton(text="Отправить геолокацию", request_location=True)]
],
	resize_keyboard=True,
	one_time_keyboard=True)