import os
import re
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q" 
ADMIN_ID = 1165444045 

# Сервер для работы Render (Health Check)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

# --- КАТАЛОГ ТОВАРОВ (ПОЛНЫЙ) ---
PRODUCTS = {
    "boxes": [
        {
            "name": "Бенто-торт из клубники (8 ягод)", 
            "price": "2490", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"
        },
        {
            "name": "Набор клубники и малины в шоколаде", 
            "price": "2990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/06/malinki-takie-vecerinki.jpg"
        },
        {
            "name": "Бокс «С надписью» Средний", 
            "price": "5990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/boks-s-nadpisyu.jpg"
        },
        {
            "name": "Корзина клубники в шоколаде S", 
            "price": "5990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/korzina-klubniki-v-shokolade-s.jpeg"
        },
        {
            "name": "Торт из клубники в шоколаде", 
            "price": "7490", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photo_2025_02_25_16_20_32_481x582.jpg"
        }
    ],
    "flowers": [
        {
            "name": "Букет «Зефирка»", 
            "price": "4490", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"
        },
        {
            "name": "Букет из роз и эустомы", 
            "price": "3490", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-iz-roz-i-eustomy.jpg"
        },
        {
            "name": "Моно букет «Диантусы»", 
            "price": "2690", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/mono-buket-diantusy.png"
        }
    ],
    "sweet": [
        {
            "name": "Букет клубничный S Ажурный", 
            "price": "3990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"
        },
        {
            "name": "Букет «Ягодное ассорти»", 
            "price": "6490", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2016/12/photo_2024-04-05_17-55-09.jpg"
        },
        {
            "name": "Букет из цельных фруктов «С любовью»", 
            "price": "3990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2016/04/photo_2022-12-09_15-56-56.jpg"
        }
    ],
    "meat": [
        {
            "name": "Букет «Мясной» стандарт", 
            "price": "5990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"
        },
        {
            "name": "Букет из королевских креветок и клешней краба", 
            "price": "9990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2018/08/photo_2022-12-09_18-05-36-2.jpg"
        },
        {
            "name": "Мужская корзина «Брутал»", 
            "price": "12990", 
            "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/whatsapp202023_10_1620v2014.38.08_14f00b4d_481x582.jpg"
        }
    ]
}

# --- ОСНОВНЫЕ ФУНКЦИИ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать в FruttoSmile!\n\nДля активации бонусов нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    phone = update.message.contact.phone_number
    
    # Сохраняем бонусы глобально для приложения
    context.application.user_data.setdefault(uid, {})['bonuses'] = 300
    context.application.user_data[uid]['phone'] = phone
    
    await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов. 🎁")
    
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    
    await update.message.reply_text("Выберите действие в меню: 🍓", reply_markup=kb)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    uid = update.effective_user.id
    
    if msg == "📊 Информация о бонусах":
        user_info = context.application.user_data.get(uid, {})
        b = user_info.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {b} бонусов.")
        
    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие букеты", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские букеты", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
        
    elif msg == "📸 Получить фото заказа":
        user_info = context.application.user_data.get(uid, {})
        if 'phone' not in user_info:
            await update.message.reply_text("Пожалуйста, сначала зарегистрируйтесь!")
        else:
            await update.message.reply_text("🔍 Запрос отправлен менеджеру! Ожидайте фото.")
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=f"🔔 ЗАПРОС ФОТО\n👤 Имя: {update.effective_user.full_name}\n🆔 ID: {uid}\n📱 Тел: {user_info['phone']}"
            )
            
    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        kb = [
            [
                InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/"), 
                InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211")
            ],
            [
                InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/"), 
                InlineKeyboardButton("VK", url="https://vk.com/fruttosmile")
            ]
        ]
        await update.message.reply_text(
            "⭐ Оставьте отзыв и пришлите скриншот сюда.\nПосле проверки мы начислим +250 бонусов!",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        
    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Иркутск, Улица Дыбовского, 8/5\n⏰ Ежедневно 09:00 - 20:00")
        
    elif msg == "🛒 Оформить заказ":
        await update.message.reply_text("🛍 Оформить заказ можно на нашем сайте: https://fruttosmile.ru")

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("cat_"):
        cat = query.data.replace("cat_", "")
        products = PRODUCTS.get(cat, [])
        await query.message.delete()
        for p in products:
            try:
                await query.message.chat.send_photo(
                    photo=p['photo'], 
                    caption=f"<b>{p['name']}</b>\n💰 Цена: {p['price']}₽", 
                    parse_mode="HTML"
                )
            except:
                await query.message.chat.send_message(f"📦 {p['name']} - {p['price']}₽")
                
    elif query.data.startswith("rev_"):
        action = query.data.split("_")[1]
        client_id = int(query.data.split("_")[2])
        
        if action == "approve":
            user_info = context.application.user_data.setdefault(client_id, {})
            current = user_info.get('bonuses', 300)
            user_info['bonuses'] = current + 250
            await context.bot.send_message(
                chat_id=client_id, 
                text=f"🎁 Ваш отзыв одобрен! Начислено +250 бонусов. Ваш баланс: {user_info['bonuses']}"
            )
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ ОДОБРЕНО")
        else:
            await context.bot.send_message(chat_id=client_id, text="❌ Отзыв отклонен модератором.")
            await query.edit_message_caption(caption=query.message.caption + "\n\n❌ ОТКЛОНЕНО")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    msg = update.message
    
    # 1. Если админ отвечает на сообщение фоточкой (Reply)
    if uid == ADMIN_ID and msg.reply_to_message:
        reply_text = msg.reply_to_message.caption or msg.reply_to_message.text or ""
        match = re.search(r"ID:\s*(\d+)", reply_text)
        if match:
            target_id = int(match.group(1))
            await context.bot.send_photo(
                chat_id=target_id, 
                photo=msg.photo[-1].file_id, 
                caption="✨ Ваше фото заказа готово! Приятного аппетита! 🍓"
            )
            await msg.reply_text(f"✅ Фото отправлено клиенту (ID: {target_id})")
            return

    # 2. Если клиент прислал скриншот отзыва
    if context.user_data.get('state') == 'WAIT_REVIEW':
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Принять (+250)", callback_data=f"rev_approve_{uid}"), 
                InlineKeyboardButton("❌ Отклонить", callback_data=f"rev_reject_{uid}")
            ]
        ])
        await msg.reply_text("✅ Скриншот принят на модерацию!")
        await context.bot.send_photo(
            chat_id=ADMIN_ID, 
            photo=msg.photo[-1].file_id, 
            caption=f"📸 НОВЫЙ ОТЗЫВ\n🆔 ID: {uid}", 
            reply_markup=kb
        )
        context.user_data['state'] = None

def main():
    # Запуск сервера
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
