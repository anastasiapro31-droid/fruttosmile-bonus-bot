import sys
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ────────────────────────────────────────────────
# КОНФИГУРАЦИЯ
# ────────────────────────────────────────────────

BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q"  # ← Замени на реальный!
ADMIN_ID = 1165444045  # ← Твой Telegram ID (менеджера)

# Простейший веб-сервер, чтобы Render не убивал бота
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# Пример товаров (можно использовать позже для каталога)
PRODUCTS = {
    "boxes": [{"name": "Бенто-торт (8 ягод)", "price": "2490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"}],
    "flowers": [{"name": "Букет «Зефирка»", "price": "4490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"}],
    "sweet": [{"name": "Букет клубничный S", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"}],
    "meat": [{"name": "Букет «Мясной»", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"}]
}

# ────────────────────────────────────────────────
# ФУНКЦИИ
# ────────────────────────────────────────────────

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    msg = "Выберите действие в меню FruttoSmile: 🍓"
    await update.effective_message.reply_text(msg, reply_markup=kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать!\n\nДля активации бонусов нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )

async def process_photo_request(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str, order_number: str = None):
    uid = update.effective_user.id
    print(f"Process photo request for user {uid} with phone {phone} and order {order_number}")  # Debug log
    await update.effective_message.reply_text("🔍 Запрос отправлен менеджеру! Мы сообщим вам статус заказа.")

    order_txt = f"\n📦 Заказ: {order_number}" if order_number else ""
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Готов", callback_data=f"st_ready_{uid}"),
            InlineKeyboardButton("⏳ В работе", callback_data=f"st_work_{uid}"),
            InlineKeyboardButton("❌ Заказа нет", callback_data=f"st_none_{uid}")
        ]
    ])

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 ЗАПРОС ФОТО\n📱 Тел: {phone}{order_txt}\n🆔 ID: {uid}",
        reply_markup=admin_kb
    )
    context.user_data.pop('state', None)

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    state = context.user_data.get('state')
    print(f"Handle contact: state={state}, phone={phone}")  # Debug log
    if state == 'WAIT_ORDER':
        await process_photo_request(update, context, phone)
    else:
        context.user_data['phone'] = phone
        context.user_data['bonuses'] = context.user_data.get('bonuses', 0) + 300
        await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов.")
        await send_main_menu(update, context)

async def show_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    print(f"Show confirmation for user {uid}")  # Debug log
    if 'phone' not in context.user_data:
        btn = KeyboardButton("📲 Подтвердить номер", request_contact=True)
        await update.effective_message.reply_text(
            "Сначала нужно подтвердить номер телефона для поиска заказа.",
            reply_markup=ReplyKeyboardMarkup([[btn], ["⬅️ Назад"]], resize_keyboard=True)
        )
        context.user_data['state'] = 'WAIT_ORDER'
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Получить фото", callback_data="confirm_photo_request"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo_request")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.effective_message.reply_text(
        "Вы действительно хотите запросить фото заказа?\n\nПосле подтверждения запрос уйдёт менеджеру.",
        reply_markup=reply_markup
    )
    context.user_data['state'] = 'AWAITING_PHOTO_CONFIRM'

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
    state = context.user_data.get('state')
    uid = update.effective_user.id
    print(f"Text handler: msg='{msg}', state={state}, user={uid}")  # Debug log для отслеживания

    if msg == "⬅️ Назад":
        context.user_data.pop('state', None)
        await send_main_menu(update, context)
        return

    if msg == "📸 Получить фото заказа":
        await show_photo_confirmation(update, context)
        return

    if state == 'WAIT_ORDER_NUMBER':
        order_number = msg
        await process_photo_request(update, context, context.user_data['phone'], order_number)
        return

    if msg == "📊 Информация о бонусах":
        if 'phone' not in context.user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь!")
        else:
            bonuses = context.user_data.get('bonuses', 0)
            await update.message.reply_text(f"🎁 Ваш баланс: {bonuses} бонусов.")
        return

    # Заглушки для остальных кнопок
    if msg in ("🛒 Оформить заказ", "📖 Каталог товаров", "⭐ Оставить отзыв", "📍 Адреса самовывоза"):
        await update.message.reply_text("Функция в разработке. Скоро будет доступна!")
        return

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    print(f"Query handler: data={data}")  # Debug log

    if data == "confirm_photo_request":
        context.user_data['state'] = 'WAIT_ORDER_NUMBER'
        await query.message.reply_text(
            "Введите номер заказа (например: 12345):",
            reply_markup=ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True)
        )
        await query.edit_message_text("Запрос подтверждён. Введите номер заказа.")

    elif data == "cancel_photo_request":
        await query.edit_message_text("Запрос отменён.")
        context.user_data.pop('state', None)
        await send_main_menu(update, context)

    elif data.startswith("st_"):
        uid = int(data.split("_")[2])
        if "ready" in data:
            txt = "✅ Заказ готов! Фото придёт скоро."
        elif "work" in data:
            txt = "⏳ Заказ в работе!"
        else:
            txt = "❌ Заказ не найден."
        await context.bot.send_message(chat_id=uid, text=txt)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not update.message.reply_to_message:
        return

    try:
        text = update.message.reply_to_message.text
        match = re.search(r'🆔 ID: (\d+)', text)
        if match:
            tid = int(match.group(1))
            photo = update.message.photo[-1].file_id
            await context.bot.send_photo(
                chat_id=tid,
                photo=photo,
                caption="📸 Ваш заказ готов!"
            )
    except Exception as e:
        print(f"Ошибка при пересылке фото: {e}")

# ────────────────────────────────────────────────
# ЗАПУСК
# ────────────────────────────────────────────────

def main():
    # Запускаем заглушку для Render в отдельном потоке
    threading.Thread(target=run_health_server, daemon=True).start()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(query_handler))

    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
