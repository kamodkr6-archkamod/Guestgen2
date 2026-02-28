import sqlite3
import requests
import json
import io
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from telegram.error import Forbidden

TOKEN = '8283329429:AAFwjmn7ctl55RtqM1sQPZBgiwAlmz-DtVw'
ADMIN_ID = 8138834246
API_URL = "https://guistg-2jzw.onrender.com/gen"
CHANNELS = ["@KAMOD_CODEX", "@KAMOD_CODEX_BACKUP", "@KAMOD_LIKE_GROUP"]

REGION, NAME, COUNT, REDEEM_INP = range(4)

# ================= DATABASE =================

def get_db_connection():
    conn = sqlite3.connect('kamod_bot.db', timeout=30, check_same_thread=False)
    conn.execute('PRAGMA journal_mode=WAL;')
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 20, referred_by INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS promo_codes 
                 (code TEXT PRIMARY KEY, value INTEGER, uses_left INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS redeemed_history 
                 (user_id INTEGER, code TEXT, PRIMARY KEY (user_id, code))''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    if not res:
        c.execute("INSERT INTO users (user_id, balance) VALUES (?, ?)", (user_id, 20))
        conn.commit()
        conn.close()
        return 20
    conn.close()
    return res[0]

def update_balance(user_id, amount):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# ================= FORCE JOIN =================

async def is_subscribed(bot, user_id):
    if user_id == ADMIN_ID:
        return True
    for channel in CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def get_join_markup():
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel 1", url="https://t.me/KAMOD_CODEX")],
        [InlineKeyboardButton("📢 Join Channel 2", url="https://t.me/KAMOD_CODEX_BACKUP")],
        [InlineKeyboardButton("📢 Join Channel 3", url="https://t.me/KAMOD_LIKE_GROUP")],
        [InlineKeyboardButton("✅ VERIFY", callback_data="verify_join")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_permanent_keyboard():
    keyboard = [
        ["🔥 GENERATE ACCOUNTS"],
        ["💰 BALANCE", "🎁 REDEEM"],
        ["👤 OWNER", "👥 REFER"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    user = update.effective_user
    user_id = user.id
    init_db()

    if not await is_subscribed(context.bot, user_id):
        await update.message.reply_text("❌ Join Channels First!", reply_markup=get_join_markup())
        return

    await update.message.reply_text(
        f"👋 Hello {user.first_name}\n💰 Balance: {get_user_data(user_id)} Coins",
        reply_markup=get_permanent_keyboard()
    )

# ================= REGION BUTTON =================

async def region_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    region = query.data.split("_")[1]
    context.user_data['region'] = region

    await query.message.edit_text(
        f"✅ REGION SELECTED ➜ {region}\n\n👤 Enter Name:"
    )
    return NAME

# ================= BUTTON HANDLER =================

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
        
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🔥 GENERATE ACCOUNTS":
        if get_user_data(user_id) <= 0:
            await update.message.reply_text("❌ Low Balance!")
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton("🇮🇳 INDIA (IND)", callback_data="reg_IND")],
            [InlineKeyboardButton("🇧🇷 BRAZIL (BRA)", callback_data="reg_BRA")],
            [InlineKeyboardButton("🇮🇩 INDONESIA (ID)", callback_data="reg_ID")]
        ]

        await update.message.reply_text(
            "🌍 SELECT YOUR REGION",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return REGION
        
    elif text == "💰 BALANCE":
        await update.message.reply_text(f"💰 Balance: {get_user_data(user_id)} Coins")
        
    elif text == "🎁 REDEEM":
        await update.message.reply_text("🎁 Enter your Redeem Code:")
        return REDEEM_INP
        
    elif text == "👤 OWNER":
        await update.message.reply_text("👤 Owner: @kamod90")
        
    elif text == "👥 REFER":
        bot_user = (await context.bot.get_me()).username
        await update.message.reply_text(f"https://t.me/{bot_user}?start={user_id}")

# ================= GENERATION =================

async def fetch_acc(params):
    loop = asyncio.get_event_loop()
    try:
        r = await loop.run_in_executor(None, lambda: requests.get(API_URL, params=params, timeout=15))
        return r.json() if r.status_code == 200 else None
    except:
        return None

async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['name'] = update.message.text
    await update.message.reply_text("Accounts Count?\n1 Coin = 1 Account")
    return COUNT

async def get_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = int(update.message.text)
    user_id = update.effective_user.id
    balance = get_user_data(user_id)

    if count > balance:
        await update.message.reply_text("❌ Low Balance!")
        return ConversationHandler.END

    msg = await update.message.reply_text(
f"""
╔══════════════════════╗
   🚀 PREMIUM GENERATOR
╚══════════════════════╝

👤 NAME ➜ {context.user_data['name']}
🌍 REGION ➜ {context.user_data['region']}
📦 COUNT ➜ {count}

━━━━━━━━━━━━━━━━━━━━━━
⚡ STARTING...
━━━━━━━━━━━━━━━━━━━━━━
"""
)

    params = {
        'name': context.user_data['name'],
        'count': 1,
        'region': context.user_data['region']
    }

    final_accs = []

    for i in range(count):
        res = await fetch_acc(params)
        if res:
            final_accs.append(res)
        await asyncio.sleep(0.2)

    update_balance(user_id, -count)

    f_io = io.BytesIO(json.dumps(final_accs, indent=4).encode())
    f_io.name = f"accounts_{user_id}.json"

    await msg.delete()

    await update.message.reply_document(
        document=f_io,
        caption=f"""
╔══════════════════════╗
   ✅ GENERATION COMPLETE
╚══════════════════════╝

📦 ACCOUNTS ➜ {len(final_accs)}
💰 BALANCE ➜ {get_user_data(user_id)} Coins
"""
    )

    return ConversationHandler.END

# ================= USER REDEEM =================

async def handle_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code_txt = update.message.text.strip()
    user_id = update.effective_user.id
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT 1 FROM redeemed_history WHERE user_id = ? AND code = ?", (user_id, code_txt))
    if c.fetchone():
        await update.message.reply_text("❌ Already Claimed!")
        conn.close()
        return ConversationHandler.END

    c.execute("SELECT value, uses_left FROM promo_codes WHERE code = ?", (code_txt,))
    res = c.fetchone()

    if res and res[1] > 0:
        val = res[0]
        c.execute("UPDATE promo_codes SET uses_left = uses_left - 1 WHERE code = ?", (code_txt,))
        c.execute("INSERT INTO redeemed_history VALUES (?, ?)", (user_id, code_txt))
        conn.commit()
        update_balance(user_id, val)
        await update.message.reply_text(f"✅ Redeemed! +{val} Coins added.")
    else:
        await update.message.reply_text("❌ Code invalid ya limit khatam!")

    conn.close()
    return ConversationHandler.END

# ================= ADMIN REDEEM =================

async def admin_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        code = context.args[0]
        val = int(context.args[1])
        uses = int(context.args[2])

        conn = get_db_connection()
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO promo_codes VALUES (?, ?, ?)", (code, val, uses))
        conn.commit()
        conn.close()

        poster = (
            "╔══════════════════════╗\n"
            "🚀  𝗡𝗘𝗪 𝗣𝗥𝗢𝗠𝗢 𝗖𝗢𝗗𝗘 𝗔𝗟𝗘𝗥𝗧  🚀\n"
            "╚══════════════════════╝\n\n"
            f"🎟️ 𝗖𝗢𝗗𝗘 ➤  `{code}`\n"
            f"💎 𝗩𝗔𝗟𝗨𝗘 ➤  {val} 𝗖𝗢𝗜𝗡𝗦\n"
            f"👥 𝗟𝗜𝗠𝗜𝗧 ➤  {uses} 𝗨𝗦𝗘𝗥𝗦\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚡ 𝗙𝗔𝗦𝗧 𝗥𝗘𝗗𝗘𝗘𝗠 𝗡𝗢𝗪!\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )

        await update.message.reply_text(poster, parse_mode="Markdown")

    except:
        await update.message.reply_text("Usage: /redeem CODE VALUE LIMIT")

# ================= MAIN =================

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^(🔥 GENERATE ACCOUNTS|🎁 REDEEM)$'), handle_buttons)],
        states={
            REGION: [],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_count)],
            REDEEM_INP: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_redeem)],
        },
        fallbacks=[CommandHandler('start', start)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("redeem", admin_redeem))
    app.add_handler(CallbackQueryHandler(region_button, pattern="reg_"))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    print("Bot is LIVE...")
    app.run_polling()

if __name__ == '__main__':
    main()