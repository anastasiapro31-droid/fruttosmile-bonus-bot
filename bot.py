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
 
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q"          # ← обязательно заменить!
ADMIN_ID = 1165444045             # ← ID менеджера
 
# Health check сервер для Render
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
 
def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()
 
# ================= ВЫБРАННЫЙ КАТАЛОГ ТОВАРОВ =================
PRODUCTS = {
    "boxes": [
        {"name": "Бенто-торт из клубники (8 ягод)", "price": "2490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"},
        {"name": "Набор клубники и малины в шоколаде", "price": "2990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/06/malinki-takie-vecerinki.jpg"},
        {"name": "Бокс «С надписью» Средний", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/boks-s-nadpisyu.jpg"},
        {"name": "Корзина клубники в шоколаде S", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/korzina-klubniki-v-shokolade-s.jpeg"},
        {"name": "Торт из клубники в шоколаде", "price": "7490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photo_2025_02_25_16_20_32_481x582.jpg"}
    ],
    "flowers": [
        {"name": "Букет «Зефирка»", "price": "4490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"},
        {"name": "Букет из роз и эустомы", "price": "3490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-iz-roz-i-eustomy.jpg"},
        {"name": "Моно букет «Диантусы»", "price": "2690", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/mono-buket-diantusy.png"}
    ],
    "sweet": [
        {"name": "Букет клубничный S Ажурный", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"},
        {"name": "Букет «Ягодное ассорти»", "price": "6490", "photo": "http://fruttosmile.su/wp-content/uploads/2016/12/photo_2024-04-05_17-55-09.jpg"},
        {"name": "Букет из цельных фруктов «С любовью»", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2016/04/photo_2022-12-09_15-56-56.jpg"}
    ],
    "meat": [
        {"name": "Букет «Мясной» стандарт", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"},
        {"name": "Букет из королевских креветок и клешней краба", "price": "9990", "photo": "http://fruttosmile.su/wp-content/uploads/2018/08/photo_2022-12-09_18-05-36-2.jpg"},
        {"name": "Мужская корзина «Брутал»", "price": "12990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/whatsapp202023_10_1620v2014.38.08_14f00b4d_481x582.jpg"}
    ]
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
 
async def process_photo_request(update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    uid = update.effective_user.id
    user = update.effective_user
 
    first_name = user.first_name or "не указано"
    last_name  = user.last_name  or ""
    username   = user.username   or "нет"
    full_name = f"{first_name} {last_name}".strip()
 
    await update.effective_message.reply_text("🔍 Запрос отправлен менеджеру!\nМы сообщим вам, когда статус изменится.")
 
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Готов",    callback_data=f"st_ready_{uid}"),
            InlineKeyboardButton("⏳ В работе", callback_data=f"st_work_{uid}"),
            InlineKeyboardButton("❌ Заказа нет", callback_data=f"st_none_{uid}")
        ]
    ])
 
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"🔔 ЗАПРОС ФОТО ЗАКАЗА\n"
            f"👤 Имя: {full_name}\n"
            f"📱 Телефон: {phone}\n"
            f"🆔 Telegram ID: {uid}\n"
            f"@{username}"
        ),
        reply_markup=admin_kb
    )
    context.user_data.pop('state', None)
 
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    state = context.user_data.get('state')
 
    if state == 'WAIT_ORDER':
        await process_photo_request(update, context, phone)
    else:
        context.user_data['phone'] = phone
        # Устанавливаем ровно 300 бонусов при регистрации
        context.user_data['bonuses'] = 300
        await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов.")
        await send_main_menu(update, context)
 
async def show_photo_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'phone' not in context.user_data:
        btn = KeyboardButton("📲 Подтвердить номер", request_contact=True)
        await update.effective_message.reply_text(
            "Для запроса фото нужно подтвердить номер телефона.",
            reply_markup=ReplyKeyboardMarkup([[btn], ["⬅️ Назад"]], resize_keyboard=True)
        )
        context.user_data['state'] = 'WAIT_ORDER'
        return
 
    keyboard = [[InlineKeyboardButton("✅ Да, запросить", callback_data="confirm_photo_request"),
                 InlineKeyboardButton("❌ Отмена", callback_data="cancel_photo_request")]]
    
    await update.effective_message.reply_text("Запросить фото заказа у менеджера?", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data['state'] = 'AWAITING_PHOTO_CONFIRM'
 
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text.strip()
 
    if msg == "⬅️ Назад":
        context.user_data.pop('state', None)
        await send_main_menu(update, context)
        return
 
    if msg == "📸 Получить фото заказа":
        await show_photo_confirmation(update, context)
        return
 
    if msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие букеты", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские букеты", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
        return
 
    if msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        kb = [[InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/"), 
               InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/")]]
        await update.message.reply_text("⭐ Оставьте отзыв и пришлите скриншот сюда для получения 250 бонусов!", reply_markup=InlineKeyboardMarkup(kb))
        return
 
    if msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Иркутск, Улица Дыбовского, 8/5\n⏰ 09:00 - 20:00")
        return
 
    if msg == "📊 Информация о бонусах":
        bonuses = context.user_data.get('bonuses', 0)
        if 'phone' not in context.user_data:
            await update.message.reply_text("Сначала зарегистрируйтесь (поделитесь номером)!")
        else:
            text = f"🎁 Ваш баланс в Fruttosmile: {bonuses} бонусов\n"
            text += "(Начислено за регистрацию)" if bonuses == 300 else "(Включая бонусы за отзывы)"
            await update.message.reply_text(text)
        return
    
    if msg == "🛒 Оформить заказ":
        kb = [[InlineKeyboardButton("🛍 Перейти на сайт", url="https://fruttosmile.ru")]]
        await update.message.reply_text("Оформить заказ можно на сайте:", reply_markup=InlineKeyboardMarkup(kb))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
 
    if data == "confirm_photo_request":
        phone = context.user_data.get('phone')
        await process_photo_request(update, context, phone)
        await query.edit_message_text("✅ Запрос отправлен менеджеру!")
 
    elif data == "cancel_photo_request":
        await query.edit_message_text("Запрос отменён.")
        await send_main_menu(update, context)
 
    elif data.startswith("cat_"):
        category = data.replace("cat_", "")
        products = PRODUCTS.get(category, [])
        await query.message.delete()
        for p in products:
            try:
                await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 {p['price']}₽", parse_mode="HTML")
            except:
                await query.message.chat.send_message(f"📦 {p['name']} - {p['price']}₽")
        await query.message.chat.send_message("Для заказа вернитесь в меню.", reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))
 
    elif data.startswith("st_"):
        uid = int(data.split("_")[2])
        msg = "✅ Заказ готов!" if "ready" in data else "⏳ Заказ в работе." if "work" in data else "❌ Заказ не найден."
        await context.bot.send_message(chat_id=uid, text=msg)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Если это отзыв от клиента
    if context.user_data.get('state') == 'WAIT_REVIEW':
        await update.message.reply_text("✅ Скриншот принят! Мы начислим бонусы после проверки.")
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                                     caption=f"📸 ОТЗЫВ от {update.message.from_user.full_name}\n🆔 ID: {update.effective_user.id}")
        context.user_data.pop('state', None)
        return

    # Если это ответ админа (фото заказа клиенту)
    if update.message.from_user.id == ADMIN_ID and update.message.reply_to_message:
        try:
            text = update.message.reply_to_message.text
            match = re.search(r'🆔 Telegram ID: (\d+)', text)
            if match:
                tid = int(match.group(1))
                await context.bot.send_photo(chat_id=tid, photo=update.message.photo[-1].file_id, caption="📸 Фото вашего заказа готово!")
                await update.message.reply_text("✅ Отправлено клиенту!")
        except:
            await update.message.reply_text("Ошибка отправки.")
 
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()
 
if __name__ == "__main__":
    main()
