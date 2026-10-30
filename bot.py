import asyncio
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ==================== CONFIG ====================
BOT_TOKEN = "9261489338:AAGW0ZlhYyCrhwa0mf43yjy4Ts_Lo7Bj3yM"
ADMIN_IDS = [7970417823]

# ==================== DATABASE ====================
DB_NAME = "shop.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                balance REAL DEFAULT 0,
                referred_by INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT,
                name TEXT,
                description TEXT,
                price REAL,
                stock INTEGER DEFAULT 0,
                delivery_text TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                product_name TEXT,
                price REAL,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS deposits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                status TEXT DEFAULT 'pending',
                proof TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# ==================== STATES ====================
class AdminStates(StatesGroup):
    add_product_category = State()
    add_product_name = State()
    add_product_desc = State()
    add_product_price = State()
    add_product_stock = State()
    add_product_delivery = State()
    add_balance_user = State()
    add_balance_amount = State()

class DepositStates(StatesGroup):
    waiting_amount = State()
    waiting_proof = State()

# ==================== KEYBOARDS ====================
def main_menu():
    kb = [
        [KeyboardButton(text="🛒 SHOP")],
        [KeyboardButton(text="💰 DEPOSIT"), KeyboardButton(text="👤 PROFILE")],
        [KeyboardButton(text="📜 HISTORY"), KeyboardButton(text="🎁 REFERRAL")],
        [KeyboardButton(text="📖 TUTORIAL"), KeyboardButton(text="📁 FILES")],
        [KeyboardButton(text="🛠 SUPPORT")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def admin_menu():
    kb = [
        [KeyboardButton(text="➕ Add Product"), KeyboardButton(text="📦 View Products")],
        [KeyboardButton(text="💵 Add Balance"), KeyboardButton(text="📊 Stats")],
        [KeyboardButton(text="🔙 User Menu")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ==================== BOT ====================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ==================== HELPERS ====================
async def get_user(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def ensure_user(user_id: int, username: str, full_name: str, referred_by: int = 0):
    async with aiosqlite.connect(DB_NAME) as db:
        user = await get_user(user_id)
        if not user:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
                (user_id, username, full_name, referred_by)
            )
            await db.commit()

# ==================== START ====================
@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    referred_by = 0
    if len(args) > 1 and args[1].isdigit():
        referred_by = int(args[1])
        if referred_by == message.from_user.id:
            referred_by = 0

    await ensure_user(
        message.from_user.id,
        message.from_user.username,
        message.from_user.full_name,
        referred_by
    )

    text = f"""
👋 <b>WELCOME TO RAJU BHAI STORE</b> ∞

👋 <b>{message.from_user.first_name}</b>, welcome to our store! 

⚡ <b>WHY CHOOSE US?</b>
• Fastest Delivery
• 100% Automated
• 24x7 Dedicated Support
• Best Competitive Prices

👇 <b>Select An Option From The Menu Below :</b>
"""
    await message.answer(text, reply_markup=main_menu())

# ==================== PROFILE ====================
@dp.message(F.text == "👤 PROFILE")
async def profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("Please /start first")
        return

    text = f"""
👤 <b>YOUR PROFILE</b>

🆔 User ID: <code>{user[0]}</code>
👤 Name: {user[2]}
💰 Balance: ₹{user[3]:.2f}
📅 Joined: {user[5][:10] if user[5] else 'N/A'}
"""
    await message.answer(text)

# ==================== DEPOSIT ====================
@dp.message(F.text == "💰 DEPOSIT")
async def deposit_start(message: Message, state: FSMContext):
    await message.answer(
        "💰 <b>DEPOSIT MONEY</b>\n\n"
        "Enter the amount you want to deposit (minimum ₹50):\n\n"
        "Example: <code>100</code>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Cancel")]],
            resize_keyboard=True
        )
    )
    await state.set_state(DepositStates.waiting_amount)

@dp.message(DepositStates.waiting_amount)
async def deposit_amount(message: Message, state: FSMContext):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled", reply_markup=main_menu())
        return

    try:
        amount = float(message.text)
        if amount < 50:
            await message.answer("Minimum deposit is ₹50")
            return
    except:
        await message.answer("Please enter a valid number")
        return

    await state.update_data(amount=amount)
    await message.answer(
        f"💰 Amount: <b>₹{amount}</b>\n\n"
        "Please pay to this UPI and send screenshot:\n\n"
        "📲 <b>UPI ID:</b> <code>yourupi@paytm</code>\n"   # ← अपना असली UPI यहाँ डालना
        "👤 Name: Raju Bhai Store\n\n"
        "After payment, send the payment screenshot here.",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="❌ Cancel")]],
            resize_keyboard=True
        )
    )
    await state.set_state(DepositStates.waiting_proof)

@dp.message(DepositStates.waiting_proof, F.photo)
async def deposit_proof(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("amount")

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO deposits (user_id, amount, proof) VALUES (?, ?, ?)",
            (message.from_user.id, amount, "photo")
        )
        await db.commit()

    for admin in ADMIN_IDS:
        try:
            await bot.send_photo(
                admin,
                message.photo[-1].file_id,
                caption=f"💰 <b>New Deposit Request</b>\n\n"
                        f"User: {message.from_user.full_name} ({message.from_user.id})\n"
                        f"Amount: ₹{amount}\n\n"
                        f"Approve with: /approve_deposit {message.from_user.id} {amount}"
            )
        except:
            pass

    await message.answer(
        "✅ Deposit request submitted!\nAdmin will approve it soon.",
        reply_markup=main_menu()
    )
    await state.clear()

@dp.message(DepositStates.waiting_proof)
async def deposit_proof_wrong(message: Message, state: FSMContext):
    if message.text == "❌ Cancel":
        await state.clear()
        await message.answer("Cancelled", reply_markup=main_menu())
        return
    await message.answer("Please send a photo (screenshot) of payment.")

# ==================== SHOP ====================
@dp.message(F.text == "🛒 SHOP")
async def shop(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT DISTINCT category FROM products WHERE stock > 0") as cursor:
            categories = await cursor.fetchall()

    if not categories:
        await message.answer("🛍 No products available right now.\n\nAdmin को प्रोडक्ट ऐड करने बोलो।")
        return

    buttons = []
    for cat in categories:
        buttons.append([InlineKeyboardButton(text=cat[0], callback_data=f"cat_{cat[0]}")])

    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_main")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("🛒 <b>Select Category:</b>", reply_markup=kb)

@dp.callback_query(F.data.startswith("cat_"))
async def show_products(callback: CallbackQuery):
    category = callback.data[4:]
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, name, price, stock FROM products WHERE category = ? AND stock > 0",
            (category,)
        ) as cursor:
            products = await cursor.fetchall()

    if not products:
        await callback.answer("No products in this category", show_alert=True)
        return

    text = f"🛒 <b>{category}</b>\n\n"
    buttons = []
    for p in products:
        text += f"• {p[1]} — ₹{p[2]} (Stock: {p[3]})\n"
        buttons.append([InlineKeyboardButton(
            text=f"Buy {p[1]} - ₹{p[2]}",
            callback_data=f"buy_{p[0]}"
        )])

    buttons.append([InlineKeyboardButton(text="🔙 Categories", callback_data="shop_back")])
    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))

@dp.callback_query(F.data == "shop_back")
async def shop_back(callback: CallbackQuery):
    await callback.message.delete()
    await shop(callback.message)

@dp.callback_query(F.data.startswith("buy_"))
async def buy_product(callback: CallbackQuery):
    product_id = int(callback.data[4:])
    user = await get_user(callback.from_user.id)

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT * FROM products WHERE id = ?", (product_id,)) as cursor:
            product = await cursor.fetchone()

    if not product or product[5] <= 0:
        await callback.answer("Out of stock!", show_alert=True)
        return

    price = product[4]
    if user[3] < price:
        await callback.answer("Insufficient balance! Please deposit first.", show_alert=True)
        return

    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, callback.from_user.id))
        await db.execute("UPDATE products SET stock = stock - 1 WHERE id = ?", (product_id,))
        await db.execute(
            "INSERT INTO orders (user_id, product_id, product_name, price) VALUES (?, ?, ?, ?)",
            (callback.from_user.id, product_id, product[2], price)
        )
        await db.commit()

    delivery = product[6] or "Product delivered. Contact support if any issue."

    await callback.message.answer(
        f"✅ <b>Purchase Successful!</b>\n\n"
        f"Product: <b>{product[2]}</b>\n"
        f"Price: ₹{price}\n\n"
        f"<b>Delivery:</b>\n{delivery}"
    )
    await callback.answer("Purchased successfully!")

# ==================== HISTORY ====================
@dp.message(F.text == "📜 HISTORY")
async def history(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT product_name, price, created_at FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 10",
            (message.from_user.id,)
        ) as cursor:
            orders = await cursor.fetchall()

    if not orders:
        await message.answer("📜 No orders yet.")
        return

    text = "📜 <b>Your Recent Orders:</b>\n\n"
    for o in orders:
        text += f"• {o[0]} — ₹{o[1]} ({o[2][:10]})\n"
    await message.answer(text)

# ==================== REFERRAL ====================
@dp.message(F.text == "🎁 REFERRAL")
async def referral(message: Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    text = f"""
🎁 <b>REFERRAL PROGRAM</b>

Share your link and earn when friends join!

🔗 Your Referral Link:
<code>{link}</code>
"""
    await message.answer(text)

# ==================== OTHER ====================
@dp.message(F.text == "📖 TUTORIAL")
async def tutorial(message: Message):
    await message.answer("📖 <b>How to use:</b>\n\n1. Deposit money\n2. Go to Shop & buy\n3. Instant delivery\n\nAny problem? Contact Support.")

@dp.message(F.text == "📁 FILES")
async def files(message: Message):
    await message.answer("📁 No files available right now.")

@dp.message(F.text == "🛠 SUPPORT")
async def support(message: Message):
    await message.answer("🛠 Contact Admin for support.\nWe are available 24×7")

# ==================== ADMIN ====================
@dp.message(F.text == "➕ Add Product")
async def admin_add_product(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Enter <b>Category</b> name:")
    await state.set_state(AdminStates.add_product_category)

@dp.message(AdminStates.add_product_category)
async def admin_cat(message: Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Enter <b>Product Name</b>:")
    await state.set_state(AdminStates.add_product_name)

@dp.message(AdminStates.add_product_name)
async def admin_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Enter <b>Description</b>:")
    await state.set_state(AdminStates.add_product_desc)

@dp.message(AdminStates.add_product_desc)
async def admin_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Enter <b>Price</b> (number only):")
    await state.set_state(AdminStates.add_product_price)

@dp.message(AdminStates.add_product_price)
async def admin_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
    except:
        await message.answer("Invalid price. Number only.")
        return
    await state.update_data(price=price)
    await message.answer("Enter <b>Stock</b> quantity:")
    await state.set_state(AdminStates.add_product_stock)

@dp.message(AdminStates.add_product_stock)
async def admin_stock(message: Message, state: FSMContext):
    try:
        stock = int(message.text)
    except:
        await message.answer("Invalid stock. Number only.")
        return
    await state.update_data(stock=stock)
    await message.answer("Enter <b>Delivery Text</b> (जो यूजर को खरीदने के बाद मिलेगा):")
    await state.set_state(AdminStates.add_product_delivery)

@dp.message(AdminStates.add_product_delivery)
async def admin_delivery(message: Message, state: FSMContext):
    data = await state.get_data()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO products (category, name, description, price, stock, delivery_text) VALUES (?, ?, ?, ?, ?, ?)",
            (data['category'], data['name'], data['desc'], data['price'], data['stock'], message.text)
        )
        await db.commit()
    await message.answer("✅ Product added successfully!", reply_markup=admin_menu())
    await state.clear()

@dp.message(F.text == "💵 Add Balance")
async def admin_add_balance(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Enter <b>User ID</b>:")
    await state.set_state(AdminStates.add_balance_user)

@dp.message(AdminStates.add_balance_user)
async def admin_bal_user(message: Message, state: FSMContext):
    try:
        uid = int(message.text)
    except:
        await message.answer("Invalid User ID")
        return
    await state.update_data(uid=uid)
    await message.answer("Enter <b>Amount</b> to add:")
    await state.set_state(AdminStates.add_balance_amount)

@dp.message(AdminStates.add_balance_amount)
async def admin_bal_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except:
        await message.answer("Invalid amount")
        return
    data = await state.get_data()
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, data['uid']))
        await db.commit()
    await message.answer(f"✅ Added ₹{amount} to user <code>{data['uid']}</code>", reply_markup=admin_menu())
    try:
        await bot.send_message(data['uid'], f"💰 Your deposit of <b>₹{amount}</b> has been approved!")
    except:
        pass
    await state.clear()

@dp.message(F.text == "📦 View Products")
async def view_products(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT id, category, name, price, stock FROM products") as cursor:
            products = await cursor.fetchall()
    if not products:
        await message.answer("No products yet.")
        return
    text = "📦 <b>All Products:</b>\n\n"
    for p in products:
        text += f"ID: {p[0]} | {p[1]} → {p[2]} | ₹{p[3]} | Stock: {p[4]}\n"
    await message.answer(text)

@dp.message(F.text == "📊 Stats")
async def stats(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as c:
            users = (await c.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM orders") as c:
            orders = (await c.fetchone())[0]
        async with db.execute("SELECT SUM(price) FROM orders") as c:
            revenue = (await c.fetchone())[0] or 0
    await message.answer(f"📊 <b>Stats</b>\n\n👥 Users: {users}\n🛒 Orders: {orders}\n💰 Revenue: ₹{revenue:.2f}")

@dp.message(F.text == "🔙 User Menu")
async def back_to_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    await message.answer("Switched to User Menu", reply_markup=main_menu())

@dp.message(Command("admin"))
async def admin_cmd(message: Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("🔐 <b>Admin Panel</b>", reply_markup=admin_menu())

@dp.message(Command("approve_deposit"))
async def approve_deposit(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        uid = int(parts[1])
        amount = float(parts[2])
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, uid))
            await db.commit()
        await message.answer(f"✅ Approved ₹{amount} for <code>{uid}</code>")
        await bot.send_message(uid, f"💰 Your deposit of <b>₹{amount}</b> has been approved!")
    except Exception as e:
        await message.answer(f"Error: {e}\n\nUsage:\n<code>/approve_deposit USER_ID AMOUNT</code>")