import os
import sqlite3
import aiohttp
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================= CONFIG =================
TOKEN = "8313776506:AAHB3H8Pivy83PmVRLI_mUOttQbapo9-L_U"
AICAFFE_KEY = "ak_live_20160ad7707f1bd923db983f743c69ff0bb95dce8f48a59b"
# ==========================================

# Database
conn = sqlite3.connect("naija_tasks.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, referrals INTEGER DEFAULT 0,
              phone TEXT, network TEXT)''')
conn.commit()

# PAYOUT FUNCTION — 100% WORKING WITH AICAFFE
async def payout_airtime(phone: str, network: str, amount: int, user_id: int):
    if phone.startswith("0"):
        phone = "+234" + phone[1:]

    payload = {
        "request_id": f"naija_{user_id}_{int(time.time())}",
        "phone": phone,
        "service_id": network.lower(),
        "amount": int(amount)
    }

    headers = {
        "Authorization": f"Bearer {AICAFFE_KEY}",
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.post("https://iacafe.com.ng/devapi/v1/airtime",
                                  json=payload, headers=headers) as resp:
                data = await resp.json()
                if data.get("success") is True:
                    c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    return True, f"₦{amount} airtime sent!\nRef: {data.get('ref','N/A')}"
                else:
                    return False, f"Failed: {data.get('message','Try again')}"
    except Exception as e:
        return False, f"Error: {str(e)}"

# COMMANDS & BUTTONS
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_id = context.args[0] if context.args else None
    c.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user.id,))
    if ref_id and ref_id.isdigit() and int(ref_id) != user.id:
        rid = int(ref_id)
        c.execute("UPDATE users SET referrals = referrals + 1, balance = balance + 200 WHERE user_id = ?", (rid,))
        c.execute("UPDATE users SET balance = balance + 200 WHERE user_id = ?", (user.id,))
    conn.commit()

    kb = [[InlineKeyboardButton("Tasks", callback_data="tasks")],
          [InlineKeyboardButton("Balance", callback_data="balance")],
          [InlineKeyboardButton("Withdraw", callback_data="withdraw")],
          [InlineKeyboardButton("Refer & Earn", callback_data="refer")]]
    await update.message.reply_text(
        "Welcome to @NaijaTaskBot!\n\n"
        "Earn real airtime daily\n"
        "Refer = ₦200 instant\n"
        "Min withdraw ₦500",
        reply_markup=InlineKeyboardMarkup(kb))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    c.execute("SELECT balance, referrals, phone, network FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone() or (0, 0, None, None)
    balance, refs, phone, network = row

    if q.data == "balance":
        await q.edit_message_text(f"Balance: ₦{balance}\nReferrals: {refs}\n\n/start")
    elif q.data == "refer":
        link = f"https://t.me/NaijaTaskBot?start={user_id}"
        await q.edit_message_text(f"Refer & Earn ₦200 EACH!\n\n{link}\n\n/start")
    elif q.data == "tasks":
        kb = [[InlineKeyboardButton("Daily Login ₦20", callback_data="daily")],
              [InlineKeyboardButton("Join Channel ₦100", callback_data="join")]]
        await q.edit_message_text("Choose task:", reply_markup=InlineKeyboardMarkup(kb))
    elif q.data == "daily":
        c.execute("UPDATE users SET balance = balance + 20 WHERE user_id = ?", (user_id,))
        conn.commit()
        await q.edit_message_text("Daily login +₦20!\n/start")
    elif q.data == "join":
        c.execute("UPDATE users SET balance = balance + 100 WHERE user_id = ?", (user_id,))
        conn.commit()
        await q.edit_message_text("Channel task +₦100!\n/start")
    elif q.data == "withdraw":
        if balance < 500:
            await q.edit_message_text("Minimum ₦500 required!\n/start")
        elif not phone or not network:
            await q.edit_message_text("Set your phone first:\n/setphone 07038368539 mtn")
        else:
            success, msg = await payout_airtime(phone, network, int(balance), user_id)
            await q.edit_message_text(f"{msg}\n\n/start")

async def setphone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        return await update.message.reply_text("Usage: /setphone 07038368539 mtn")
    phone, net = context.args
    c.execute("UPDATE users SET phone = ?, network = ? WHERE user_id = ?", (phone, net.lower(), update.effective_user.id))
    conn.commit()
    await update.message.reply_text(f"Phone saved: {phone} ({net.upper()})\nReady to withdraw!")

# START THE BOT
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setphone", setphone))
    app.add_handler(CallbackQueryHandler(button))
    print("NaijaTaskBot is ONLINE & PAYING!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())