import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ==============================
# CONFIGURATION
# ==============================

BOT_TOKEN = "8957069742:AAH0WbOeHv6EQqOlr2e33I2futoU5rqZhzU"
ADMIN_ID = 6081767690

# SMM Panel Details
SMM_API_URL = "https://topfollower.in/api/v2"
SMM_API_KEY = "53cd904c4c29f42acec5b8b52c9bc015"

# Payment Details
UPI_ID = "6392702903@axl"
CONTACT_USERNAME = "@RD3B4T"
QR_IMAGE = "qr.png"
PROFIT_MARGIN = 1.25

# Automated UPI Gateway Configuration (Replace with your merchant gateway API details)
UPI_GATEWAY_URL = "https://api.yourgateway.com/v1/verify_utr"
UPI_GATEWAY_KEY = "your_gateway_secret_key"

# ==============================
# DATABASE (Text Files)
# ==============================

DB_FILE = "users.txt"
UTR_FILE = "used_utrs.txt"

if not os.path.exists(DB_FILE):
    open(DB_FILE, "w").close()

if not os.path.exists(UTR_FILE):
    open(UTR_FILE, "w").close()

def get_balance(user_id):
    try:
        with open(DB_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == 2 and parts[0] == str(user_id):
                    return float(parts[1])
    except Exception:
        pass
    return 0.0

def set_balance(user_id, amount):
    lines = []
    found = False
    try:
        with open(DB_FILE, "r") as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) == 2 and parts[0] == str(user_id):
                    lines.append(f"{parts[0]}|{amount}\n")
                    found = True
                else:
                    lines.append(line)
    except Exception:
        pass
    if not found:
        lines.append(f"{user_id}|{amount}\n")
    with open(DB_FILE, "w") as f:
        f.writelines(lines)

def is_utr_used(utr):
    try:
        with open(UTR_FILE, "r") as f:
            utrs = [line.strip() for line in f.readlines()]
            return utr in utrs
    except Exception:
        return False

def mark_utr_used(utr):
    with open(UTR_FILE, "a") as f:
        f.write(f"{utr}\n")

# ==============================
# AUTOMATED UTR VERIFIER
# ==============================

def verify_upi_payment(utr: str):
    """
    Calls your merchant gateway API to verify payment by UTR.
    Must return a tuple: (is_success: bool, amount: float, message: str)
    """
    try:
        # Example API call structure:
        # payload = {"key": UPI_GATEWAY_KEY, "utr": utr}
        # response = requests.post(UPI_GATEWAY_URL, json=payload, timeout=15)
        # data = response.json()
        #
        # if data.get("status") == "SUCCESS":
        #     return True, float(data.get("amount")), "Payment verified"
        
        # --- Fallback dummy mock for demonstration (remove when plugging real gateway) ---
        return False, 0.0, "Gateway not configured. Add your merchant API endpoint in UPI_GATEWAY_URL."
    except Exception as e:
        return False, 0.0, f"Gateway connection error: {str(e)}"

# ==============================
# SMM API
# ==============================

def get_services():
    try:
        r = requests.post(SMM_API_URL, data={"key": SMM_API_KEY, "action": "services"}, timeout=15)
        return r.json()
    except Exception:
        return []

def create_order(service, link, quantity):
    try:
        r = requests.post(
            SMM_API_URL,
            data={"key": SMM_API_KEY, "action": "add", "service": service, "link": link, "quantity": quantity},
            timeout=20
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}

# ==============================
# BOT HANDLERS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if get_balance(user_id) == 0:
        set_balance(user_id, 0.0)

    buttons = [
        [InlineKeyboardButton("📋 Services", callback_data="services")],
        [InlineKeyboardButton("🔎 Search", callback_data="search"), InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("💳 Add Balance", callback_data="add_balance")],
        [InlineKeyboardButton("📞 Support", url=f"https://t.me/{CONTACT_USERNAME.replace('@', '')}")]
    ]

    text = (
        "🔥 *Welcome to Paid SMM Bot*\n\n"
        f"📞 *Support:* {CONTACT_USERNAME}\n"
        "⚡ Fast & Automated Services\n\n"
        "━━━━━━━━━━━━━━\n"
        "📝 *Order Format:*\n"
        "`service_id|link|quantity`\n\n"
        "📌 *Example:*\n"
        "`7557|https://instagram.com/reel/abc|1000`\n"
        "━━━━━━━━━━━━━━"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

async def buttons_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "services":
        services = get_services()
        if not services or not isinstance(services, list):
            await query.message.reply_text("❌ Services load nahi ho saki.")
            return

        text = "📋 *AVAILABLE SERVICES*\n\n"
        for s in services[:15]:
            rate = float(s.get('rate', 0)) * PROFIT_MARGIN
            safe_name = str(s.get('name', '')).replace('*', '').replace('_', '')
            text += f"🆔 `{s['service']}` — *{safe_name}*\n💵 ₹{rate:.2f}/k | Min: {s.get('min')} | Max: {s.get('max')}\n\n"
        await query.message.reply_text(text, parse_mode="Markdown")

    elif query.data == "search":
        context.user_data["awaiting_search"] = True
        context.user_data["awaiting_utr"] = False
        await query.message.reply_text("🔎 Service name ya keyword enter karein:")

    elif query.data == "balance":
        bal = get_balance(query.from_user.id)
        await query.message.reply_text(f"💰 *Aapka Current Balance:* ₹{bal:.2f}", parse_mode="Markdown")

    elif query.data == "add_balance":
        context.user_data["awaiting_utr"] = True
        context.user_data["awaiting_search"] = False

        caption = (
            "💳 *AUTOMATIC UPI RECHARGE*\n\n"
            f"🆔 *UPI ID:* `{UPI_ID}`\n\n"
            "📌 *Instructions:*\n"
            "1. Diye gaye QR / UPI ID par payment complete karein.\n"
            "2. Payment receipt se **12-digit UTR / Ref No** copy karein.\n"
            "3. Chat me apna **12-digit UTR number** bhej kar submit karein.\n\n"
            "⚡ Balance 5 seconds me automatically credit ho jayega!"
        )
        if os.path.exists(QR_IMAGE):
            with open(QR_IMAGE, "rb") as photo:
                await query.message.reply_photo(photo=photo, caption=caption, parse_mode="Markdown")
        else:
            await query.message.reply_text(caption, parse_mode="Markdown")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    user_id = update.effective_user.id

    # 1. Handle Automated UTR Submission
    if context.user_data.get("awaiting_utr") or (len(msg) == 12 and msg.isdigit()):
        context.user_data["awaiting_utr"] = False
        utr = msg

        if not (len(utr) == 12 and utr.isdigit()):
            await update.message.reply_text("❌ Invalid UTR! Kripya sahi 12-digit UTR number bhejein.")
            return

        if is_utr_used(utr):
            await update.message.reply_text("❌ Yeh UTR pehle hi use ho chuka hai!")
            return

        status_msg = await update.message.reply_text("⏳ UTR verify kiya ja raha hai, kripya wait karein...")

        # Verify through Gateway
        success, amount, err_msg = verify_upi_payment(utr)

        if success and amount > 0:
            # Mark UTR as used immediately to block race conditions
            mark_utr_used(utr)
            current_bal = get_balance(user_id)
            new_bal = current_bal + amount
            set_balance(user_id, new_bal)

            await status_msg.edit_text(
                f"✅ *PAYMENT VERIFIED AUTOMATICALLY!*\n\n"
                f"🔢 *UTR:* `{utr}`\n"
                f"💵 *Amount Added:* ₹{amount:.2f}\n"
                f"💰 *New Balance:* ₹{new_bal:.2f}",
                parse_mode="Markdown"
            )

            # Notify Admin
            try:
                await context.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=f"🔔 *Auto Deposit Alert*\nUser: `{user_id}`\nAmount: ₹{amount:.2f}\nUTR: `{utr}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        else:
            await status_msg.edit_text(f"❌ *Verification Failed*\nReason: {err_msg}", parse_mode="Markdown")
        return

    # 2. Handle Search
    if context.user_data.get("awaiting_search"):
        services = get_services()
        found = []
        if isinstance(services, list):
            for s in services:
                if msg.lower() in str(s.get("name", "")).lower():
                    rate = float(s.get("rate", 0)) * PROFIT_MARGIN
                    safe_name = str(s.get("name", "")).replace('*', '').replace('_', '')
                    found.append(f"🆔 `{s['service']}` — *{safe_name}*\n💵 Rate: ₹{rate:.2f}/k")
                if len(found) >= 10:
                    break

        context.user_data["awaiting_search"] = False
        if found:
            await update.message.reply_text("\n\n".join(found), parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Service nahi mili.")
        return

    # 3. Handle Order Placement (format: id|link|quantity)
    if "|" in msg:
        parts = [p.strip() for p in msg.split("|")]
        if len(parts) != 3:
            await update.message.reply_text("❌ Sahi format: `service_id|link|quantity`", parse_mode="Markdown")
            return

        service_id, link, qty_str = parts
        if not qty_str.isdigit():
            await update.message.reply_text("❌ Quantity number me honi chahiye.")
            return

        quantity = int(qty_str)
        services = get_services()
        target_service = None

        if isinstance(services, list):
            for s in services:
                if str(s.get("service")) == service_id:
                    target_service = s
                    break

        if not target_service:
            await update.message.reply_text("❌ Invalid Service ID.")
            return

        rate = float(target_service.get("rate", 0)) * PROFIT_MARGIN
        cost = (rate / 1000) * quantity
        current_bal = get_balance(user_id)

        if current_bal < cost:
            await update.message.reply_text(
                f"❌ *Low Balance!*\n\n"
                f"💸 Order Cost: ₹{cost:.2f}\n"
                f"💰 Current Balance: ₹{current_bal:.2f}\n\n"
                "Balance add karne ke liye 'Add Balance' button dabayein.",
                parse_mode="Markdown"
            )
            return

        order_res = create_order(service_id, link, quantity)
        if isinstance(order_res, dict) and "order" in order_res:
            new_bal = current_bal - cost
            set_balance(user_id, new_bal)
            order_id = str(order_res['order']).replace('_', r'\_')
            await update.message.reply_text(
                f"✅ *ORDER PLACED!*\n\n"
                f"🆔 Order ID: `{order_id}`\n"
                f"📦 Quantity: {quantity}\n"
                f"💸 Deducted: ₹{cost:.2f}\n"
                f"💰 Balance Left: ₹{new_bal:.2f}\n\n"
                f"📞 Support: {CONTACT_USERNAME}",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(f"❌ Order Failed: {order_res}")

async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        target_uid = int(context.args[0])
        amt = float(context.args[1])
        new_bal = get_balance(target_uid) + amt
        set_balance(target_uid, new_bal)
        await update.message.reply_text(
            f"✅ Balance added!\nUser: `{target_uid}`\nAmount: ₹{amt}\nNew Balance: ₹{new_bal:.2f}",
            parse_mode="Markdown"
        )
        await context.bot.send_message(
            chat_id=target_uid,
            text=f"🎉 Aapke account me ₹{amt} credit ho gaye hain!\nTotal Balance: ₹{new_bal:.2f}"
        )
    except Exception:
        await update.message.reply_text("Usage:\n`/add userid amount`\nExample:\n`/add 6081767690 100`", parse_mode="Markdown")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", admin_add_balance))
    app.add_handler(CallbackQueryHandler(buttons_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print(f"🚀 Bot is running with UPI ID: {UPI_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
