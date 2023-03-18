from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from collections import Counter
from menu import menu

import config
import logging

logging.basicConfig(level=logging.INFO)

bot = Bot(config.token)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


class States(StatesGroup):
    pizza_order = State()
    phone = State()


kb_main = [[types.KeyboardButton("🍕 Order pizza")],
           [types.KeyboardButton("❓ FAQ"), types.KeyboardButton("📖 Order history")]]

kb = types.ReplyKeyboardMarkup(kb_main, resize_keyboard=True)

kb_pizza = [[types.KeyboardButton("✅ Accept Order")],
            [types.KeyboardButton("🚫 Cancel")]]

kb2 = types.ReplyKeyboardMarkup(kb_pizza, resize_keyboard=True)

kb_c = types.ReplyKeyboardMarkup(resize_keyboard=True).add(types.KeyboardButton("🚫 Cancel"))


# inline_button = types.InlineKeyboardButton("Add to cart", callback_data="Pizza")
# kb_a = types.InlineKeyboardMarkup().add(inline_button)


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    await message.answer("Hi, for <b>order a pizza</b> use the button and check out our menu. 👇", reply_markup=kb,
                         parse_mode=types.ParseMode.HTML)


@dp.message_handler(Text(equals="📖 Order history"))
async def history(message: types.Message):
    await message.answer("You don't have any orders yet.")


@dp.message_handler(Text(equals="🍕 Order pizza"))
async def order(message: types.Message, state: FSMContext):
    await message.answer("This is our menu, choice pizza👇", reply_markup=kb2)
    for i in menu:
        inline_button = types.InlineKeyboardButton("Add to cart🛒", callback_data=f"{i['Name']}/{i['Price']}")
        kb_a = types.InlineKeyboardMarkup().add(inline_button)

        await bot.send_photo(message.chat.id, i["image"],
                             f"{i['Name']}\nPrice: {i['Price']}$", reply_markup=kb_a)
    await States.pizza_order.set()


@dp.message_handler(Text(equals="✅ Accept Order"), state=States.pizza_order)
async def accept(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            order_l = data["list"]
    except KeyError:
        await message.answer("Your order is empty.", reply_markup=kb)
        await state.finish()
    else:
        await message.answer(
            "Now please enter your phone number 📲.\nIn a few minutes, the operator will contact you to find out your address for sending the order 🤙.",
            reply_markup=kb_c)
        await States.phone.set()


@dp.message_handler(lambda message: message.text.startswith("+") and len(message.text) == 13, state=States.phone)
async def order_final(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        order_l = data["list"]
        order_w = list(set(order_l))  # [i for i, _ in groupby(order_l)]
        price = data["price"]

    list1 = []
    c = Counter(order_l)
    for i in order_w:
        list1.append(f"{i} ({c[i]}x)\n")

    list1 = "".join(list1)
    await message.answer(f"Thanks, wait for your call.\n\nYour order is:\n{list1}\nTo pay: {str(price)}$",
                         reply_markup=kb)
    print(f"New order:\n {list1}\nTo pay: {str(price)}$Phone: {message.text}")
    await state.finish()


@dp.message_handler(Text(equals="🚫 Cancel"), state=States.phone)
async def cancel(message: types.Message, state: FSMContext):
    await message.answer("Order have been canceled.", reply_markup=kb)
    await state.finish()


@dp.message_handler(state=States.phone)
async def order_fail(message: types.Message, state: FSMContext):
    await message.answer("This is not valid phone number.")


@dp.callback_query_handler(lambda c: c.data, state=States.pizza_order)
async def order_list(callback_query: types.CallbackQuery, state: FSMContext):
    data_call = callback_query.data.split("/")
    text = data_call[0]
    await callback_query.message.answer(f"{text} has been added to order list ✔.")
    async with state.proxy() as data:
        try:
            data["list"].append(text)
            data["price"] = float(data["price"]) + float(data_call[1])
        except:
            data["list"] = [text]
            data["price"] = float(data_call[1])


@dp.message_handler(Text(equals="🚫 Cancel"), state=States.pizza_order)
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Order have been canceled.", reply_markup=kb)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
