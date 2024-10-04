import asyncio
import random

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from config import TOKEN
import sqlite3
import aiohttp
import logging
import requests

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Установка уровня логирования
logging.basicConfig(level=logging.INFO)

# Кнопки для клавиатуры
btn_register = KeyboardButton(text="Регистрация в боте")
btn_currency = KeyboardButton(text="Курс валют")
btn_saving_tips = KeyboardButton(text="Экономия")
btn_personal_finance = KeyboardButton(text="Финансы")

# Создание клавиатуры
menu_kb = ReplyKeyboardMarkup(keyboard=[
    [btn_register, btn_currency],
    [btn_saving_tips, btn_personal_finance]
], resize_keyboard=True)

# Работа с базой данных
conn = sqlite3.connect('user.db')
cursor = conn.cursor()

# Создание таблицы пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
   id INTEGER PRIMARY KEY,
   telegram_id INTEGER UNIQUE,
   name TEXT,
   category1 TEXT,
   category2 TEXT,
   category3 TEXT,
   expenses1 REAL,
   expenses2 REAL,
   expenses3 REAL
   )
''')

conn.commit()


# Определение состояний формы
class FinanceForm(StatesGroup):
    category1 = State()
    expenses1 = State()
    category2 = State()
    expenses2 = State()
    category3 = State()
    expenses3 = State()


# Команда /start
@dp.message(Command('start'))
async def start_handler(message: Message):
    await message.answer("Здравствуйте! Я ваш помощник в управлении финансами. Выберите опцию:", reply_markup=menu_kb)


# Обработка команды "Регистрация в боте"
@dp.message(F.text == "Регистрация в боте")
async def register_user(message: Message):
    user_id = message.from_user.id
    user_name = message.from_user.full_name
    cursor.execute('''SELECT * FROM users WHERE telegram_id = ?''', (user_id,))
    existing_user = cursor.fetchone()

    if existing_user:
        await message.answer("Вы уже зарегистрированы!")
    else:
        cursor.execute('''INSERT INTO users (telegram_id, name) VALUES (?, ?)''', (user_id, user_name))
        conn.commit()
        await message.answer("Регистрация прошла успешно!")


# Обработка команды "Курс валют"
@dp.message(F.text == "Курс валют")
async def show_exchange_rates(message: Message):
    url = "https://v6.exchangerate-api.com/v6/09edf8b2bb246e1f801cbfba/latest/USD"
    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            await message.answer("Не удалось получить информацию о валюте.")
            return

        usd_to_rub = data['conversion_rates']['RUB']
        eur_to_usd = data['conversion_rates']['EUR']
        eur_to_rub = eur_to_usd * usd_to_rub

        await message.answer(f"1 USD - {usd_to_rub:.2f}  RUB\n"
                             f"1 EUR - {eur_to_rub:.2f}  RUB")
    except:
        await message.answer("Произошла ошибка при получении данных.")


# Обработка команды "Экономия"
@dp.message(F.text == "Экономия")
async def share_saving_tips(message: Message):
    tips = [
        "Совет 1: Составляйте и следите за своим бюджетом.",
        "Совет 2: Откладывайте минимум 10% дохода на сбережения.",
        "Совет 3: Покупайте товары по акциям или на распродажах.",
        "Совет 4: Избегайте импульсивных покупок, планируйте покупки заранее.",
        "Совет 5: Используйте скидочные карты и бонусные программы."
        ]
    selected_tip = random.choice(tips)
    await message.answer(selected_tip)


# Обработка команды "Финансы"
@dp.message(F.text == "Финансы")
async def manage_finances(message: Message, state: FSMContext):
    await state.set_state(FinanceForm.category1)
    await message.reply("Введите первую категорию ваших расходов:")


@dp.message(FinanceForm.category1)
async def set_category1(message: Message, state: FSMContext):
    await state.update_data(category1=message.text)
    await state.set_state(FinanceForm.expenses1)
    await message.reply("Укажите расходы для первой категории:")


@dp.message(FinanceForm.expenses1)
async def set_expenses1(message: Message, state: FSMContext):
    await state.update_data(expenses1=float(message.text))
    await state.set_state(FinanceForm.category2)
    await message.reply("Введите вторую категорию расходов:")


@dp.message(FinanceForm.category2)
async def set_category2(message: Message, state: FSMContext):
    await state.update_data(category2=message.text)
    await state.set_state(FinanceForm.expenses2)
    await message.reply("Укажите расходы для второй категории:")


@dp.message(FinanceForm.expenses2)
async def set_expenses2(message: Message, state: FSMContext):
    await state.update_data(expenses2=float(message.text))
    await state.set_state(FinanceForm.category3)
    await message.reply("Введите третью категорию расходов:")


@dp.message(FinanceForm.category3)
async def set_category3(message: Message, state: FSMContext):
    await state.update_data(category3=message.text)
    await state.set_state(FinanceForm.expenses3)
    await message.reply("Укажите расходы для третьей категории:")


@dp.message(FinanceForm.expenses3)
async def save_finances(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = message.from_user.id
    cursor.execute(
        '''UPDATE users SET category1 = ?, expenses1 = ?, category2 = ?, expenses2 = ?, category3 = ?, expenses3 = ? WHERE telegram_id = ?''',
        (data['category1'], data['expenses1'], data['category2'], data['expenses2'], data['category3'],
         float(message.text), user_id))
    conn.commit()
    await state.clear()
    await message.answer("Ваши данные успешно сохранены!")


# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

