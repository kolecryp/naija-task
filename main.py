import os
import sqlite3
import aiohttp
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8313776506:AAHB3H8Pivy83PmVRLI_mUOttQbapo9-L_U"
AICAFFE_KEY = "ak_live_20160ad7707f1bd923db983f743c69ff0bb95dce8f48a59b"

conn = sqlite3.connect("naija_tasks.db", check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, referrals INTEGER DEFAULT 0,
              phone TEXT, network TEXT)''')
conn.commit()

async def payout_airtime(phone, network, amount, user_id):
    if phone.startswith('0'):
        phone = '+234' + phone[1:]

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

    url = "https://iacafe.com.ng/devapi/v1/airtime"

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
              if data.get("success") is True:
                    c.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (user_id,))
                    conn.commit()
                    return True, f"₦{amount} airtime sent instantly!\nRef: {data.get('ref','N/A')}"
                else:
                    return False, f"Failed: {data.get('message','Try again')}"
    except:
        return False, "Network error — retrying..."

# Your existing start, button, setphone handlers (keep them exactly as they are)

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("setphone", set_phone))
app.add_handler(CallbackQueryHandler(button))
print("NaijaTaskBot is LIVE & PAYING with Aicafe!")
app.run_polling()