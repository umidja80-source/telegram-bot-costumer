import asyncio
import time
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

CUSTOMER_BOT_TOKEN = "8908187461:AAHT-RhnhHdpAkm6hDDKqTRwilWGLjHjxgk"
WORKER_BOT_TOKEN   = "8906343763:AAHiayqVtXGiad2SDV4BP2yq15WI7uG-Dac"
WORKER_CHAT_ID     = 1200329840

MENU = {
    "Pitsa": [
        {"name": "Margarita",     "price": 35000},
        {"name": "Pepperoni",     "price": 42000},
        {"name": "Tort pishloq",  "price": 45000},
        {"name": "Hawai",         "price": 40000},
    ],
    "Burger": [
        {"name": "Classic Burger","price": 28000},
        {"name": "Cheese Burger", "price": 32000},
        {"name": "Chicken Burger","price": 30000},
        {"name": "Double Smash",  "price": 45000},
    ],
    "Lavash": [
        {"name": "Chicken Lavash","price": 22000},
        {"name": "Beef Lavash",   "price": 25000},
        {"name": "Mix Lavash",    "price": 27000},
    ],
    "Ichimliklar": [
        {"name": "Coca-Cola 0.5", "price": 8000},
        {"name": "Pepsi 0.5",     "price": 8000},
        {"name": "Limonad",       "price": 12000},
        {"name": "Choy",          "price": 6000},
    ],
    "Desertlar": [
        {"name": "Tiramisu",      "price": 18000},
        {"name": "Cheesecake",    "price": 20000},
        {"name": "Shokolad keki", "price": 15000},
    ],
}

class OrderState(StatesGroup):
    choosing_category = State()
    choosing_items    = State()
    entering_address  = State()
    entering_phone    = State()
    confirming        = State()

router = Router()

def fmt(amount):
    return str(amount) + " som"

def cart_text(cart):
    if not cart:
        return "Savat bosh"
    lines = ["Sizning savatingiz:\n"]
    total = 0
    for i, item in enumerate(cart, 1):
        sub = item["price"] * item["qty"]
        total += sub
        lines.append(str(i) + ". " + item["name"] + " x " + str(item["qty"]) + " = " + fmt(sub))
    lines.append("\nJami: " + fmt(total))
    return "\n".join(lines)

def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Menyu"), KeyboardButton(text="Savat")],
            [KeyboardButton(text="Buyurtma berish"), KeyboardButton(text="Yordam")],
        ],
        resize_keyboard=True
    )

def cat_kb():
    btns = []
    for cat in MENU:
        btns.append([InlineKeyboardButton(text=cat, callback_data="cat_" + cat)])
    btns.append([InlineKeyboardButton(text="Orqaga", callback_data="back_main")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

def items_kb(category, cart):
    items = MENU[category]
    btns = []
    for item in items:
        qty = next((c["qty"] for c in cart if c["name"] == item["name"]), 0)
        btns.append([InlineKeyboardButton(
            text=item["name"] + " - " + fmt(item["price"]),
            callback_data="noop"
        )])
        if qty > 0:
            btns.append([
                InlineKeyboardButton(text="-", callback_data="dec_" + category + "_" + item["name"]),
                InlineKeyboardButton(text=str(qty) + " ta", callback_data="noop"),
                InlineKeyboardButton(text="+", callback_data="inc_" + category + "_" + item["name"]),
            ])
        else:
            btns.append([
                InlineKeyboardButton(text="Qoshish", callback_data="inc_" + category + "_" + item["name"]),
            ])
    btns.append([
        InlineKeyboardButton(text="Kategoriyalar", callback_data="back_categories"),
        InlineKeyboardButton(text="Savat", callback_data="view_cart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=btns)
def cart_kb(cart):
    btns = []
    if cart:
        btns.append([
            InlineKeyboardButton(text="Buyurtma berish", callback_data="checkout"),
            InlineKeyboardButton(text="Tozalash", callback_data="clear_cart"),
        ])
    btns.append([InlineKeyboardButton(text="Menyuga", callback_data="back_categories")])
    return InlineKeyboardMarkup(inline_keyboard=btns)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Xush kelibsiz!\n\nRestoran Delivery Botga xush kelibsiz!\nMazali taomlarimizdan buyurtma bering!",
        reply_markup=main_kb()
    )

@router.message(F.text == "Menyu")
async def show_menu(message: Message, state: FSMContext):
    await state.set_state(OrderState.choosing_category)
    await message.answer("Kategoriyani tanlang:", reply_markup=cat_kb())

@router.message(F.text == "Savat")
async def show_cart(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    await message.answer(cart_text(cart), reply_markup=cart_kb(cart))

@router.message(F.text == "Buyurtma berish")
async def start_checkout(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await message.answer("Savat bosh! Avval menyudan taom tanlang.")
        return
    await state.set_state(OrderState.entering_address)
    await message.answer(
        "Yetkazib berish manzilini yozing:\n(Kocha, uy raqami, moljal)",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(F.text == "Yordam")
async def help_msg(message: Message):
    await message.answer(
        "Yordam:\n1. Menyu - taomlarni korish\n2. Savat - tanlangan taomlar\n3. Buyurtma berish - zakaz qilish",
        reply_markup=main_kb()
    )

@router.callback_query(F.data.startswith("cat_"))
async def cat_chosen(call: CallbackQuery, state: FSMContext):
    category = call.data[4:]
    data = await state.get_data()
    cart = data.get("cart", [])
    await state.set_state(OrderState.choosing_items)
    await state.update_data(current_category=category)
    await call.message.edit_text(
        category + "\n\nTaom tanlang:",
        reply_markup=items_kb(category, cart)
    )

@router.callback_query(F.data.startswith("inc_"))
async def add_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    category = parts[1]
    item_name = parts[2]
    data = await state.get_data()
    cart = data.get("cart", [])
    item_info = next((i for i in MENU[category] if i["name"] == item_name), None)
    if not item_info:
        await call.answer("Mahsulot topilmadi!")
        return
    existing = next((c for c in cart if c["name"] == item_name), None)
    if existing:
        existing["qty"] += 1
    else:
        cart.append({"name": item_name, "price": item_info["price"], "qty": 1})
    await state.update_data(cart=cart)
    await call.message.edit_reply_markup(reply_markup=items_kb(category, cart))
    await call.answer(item_name + " savatga qoshildi!")

@router.callback_query(F.data.startswith("dec_"))
async def dec_item(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    category = parts[1]
    item_name = parts[2]
    data = await state.get_data()
    cart = data.get("cart", [])
    existing = next((c for c in cart if c["name"] == item_name), None)
    if existing:
        existing["qty"] -= 1
        if existing["qty"] <= 0:
            cart.remove(existing)
    await state.update_data(cart=cart)
    await call.message.edit_reply_markup(reply_markup=items_kb(category, cart))
    await call.answer("Kamaytildi")

@router.callback_query(F.data == "view_cart")
async def view_cart(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    await call.message.edit_text(cart_text(cart), reply_markup=cart_kb(cart))
    @router.callback_query(F.data == "clear_cart")
    async def clear_cart(call: CallbackQuery, state: FSMContext):
      await state.update_data(cart=[])
      await call.message.edit_text(
        "Savat tozalandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Menyuga", callback_data="back_categories")
        ]])
    )
    await call.answer("Savat boshатildi")

@router.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    if not cart:
        await call.answer("Savat bosh!")
        return
    await state.set_state(OrderState.entering_address)
    await call.message.answer(
        "Yetkazib berish manzilini yozing:\n(Kocha nomi, uy raqami, moljal)",
        reply_markup=ReplyKeyboardRemove()
    )
    await call.answer()

@router.message(OrderState.entering_address)
async def get_address(message: Message, state: FSMContext):
    await state.update_data(address=message.text)
    await state.set_state(OrderState.entering_phone)
    contact_kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.answer(
        "Telefon raqamingizni yuboring:\nYetkazuvchi siz bilan bogllanishi uchun kerak\n\nPastdagi tugmani bosing yoki qolda kiriting (+998901234567)",
        reply_markup=contact_kb
    )

@router.message(OrderState.entering_phone, F.contact)
async def get_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await state.update_data(phone=phone)
    await show_confirm(message, state)

@router.message(OrderState.entering_phone, F.text)
async def get_phone_text(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not (phone.startswith("+998") and len(phone) >= 13):
        await message.answer("Notogri format. Masalan: +998901234567")
        return
    await state.update_data(phone=phone)
    await show_confirm(message, state)

async def show_confirm(message: Message, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    address = data.get("address", "")
    phone = data.get("phone", "")
    total = sum(i["price"] * i["qty"] for i in cart)
    items_text = "\n".join(
        "  " + i["name"] + " x " + str(i["qty"]) + " = " + fmt(i["price"] * i["qty"])
        for i in cart
    )
    text = (
        "Buyurtmangizni tasdiqlang:\n\n"
        + items_text
        + "\n\nJami: " + fmt(total)
        + "\nManzil: " + address
        + "\nTelefon: " + phone
        + "\n\nTasdiqlaysizmi?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Tasdiqlash", callback_data="confirm_order"),
        InlineKeyboardButton(text="Bekor qilish", callback_data="cancel_order"),
    ]])
    await state.set_state(OrderState.confirming)
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "confirm_order")
async def confirm_order(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get("cart", [])
    address = data.get("address", "")
    phone = data.get("phone", "")
    user = call.from_user
    total = sum(i["price"] * i["qty"] for i in cart)
    order_id = int(time.time()) % 100000
    items_text = "\n".join(
        "  " + i["name"] + " x " + str(i["qty"]) + " - " + fmt(i["price"] * i["qty"])
        for i in cart
    )
    worker_msg = (
        "YANGI BUYURTMA #" + str(order_id) + "\n"
        "------------------------\n"
        + items_text + "\n"
        "------------------------\n"
        "Jami: " + fmt(total) + "\n"
        "Manzil: " + address + "\n"
        "Telefon: " + phone + "\n"
        "Mijoz: " + user.full_name + "\n"
        "TG ID: " + str(user.id)
    )
    worker_kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Qabul qilish", callback_data="accept_" + str(order_id) + "_" + str(user.id)),
        InlineKeyboardButton(text="Rad etish", callback_data="reject_" + str(order_id) + "_" + str(user.id)),
    ]])
    try:
        worker_bot = Bot(token=WORKER_BOT_TOKEN)
        await worker_bot.send_message(WORKER_CHAT_ID, worker_msg, reply_markup=worker_kb)
        await worker_bot.session.close()
    except Exception as e:
        print("Xato:", e)
    await state.clear()
    await call.message.edit_text(
        "Buyurtma #" + str(order_id) + " qabul qilindi!\n\nTez orada ishchi siz bilan bogllanadi.\nTelefon: " + phone + "\n\nTayyorlash vaqti: 30-45 daqiqa"
    )
    await call.message.answer("Yana buyurtma berish uchun:", reply_markup=main_kb())

@router.callback_query(F.data == "cancel_order")
async def cancel_order(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Buyurtma bekor qilindi.")
    await call.message.answer("Bosh menyu:", reply_markup=main_kb())

@router.callback_query(F.data == "back_categories")
async def back_categories(call: CallbackQuery, state: FSMContext):
    await state.set_state(OrderState.choosing_category)
    await call.message.edit_text("Kategoriyani tanlang:", reply_markup=cat_kb())

@router.callback_query(F.data == "back_main")
async def back_main(call: CallbackQuery, state: FSMContext):
    await call.message.delete()
    await call.message.answer("Bosh menyu:", reply_markup=main_kb())

@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()

async def main():
    bot = Bot(token=CUSTOMER_BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    print("Mijoz boti ishga tushdi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
