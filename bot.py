import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q"
ADMIN_ID = 1165444045 

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
        {"name": "Букет из королевских креветок", "price": "9990", "photo": "http://fruttosmile.su/wp-content/uploads/2018/08/photo_2022-12-09_18-05-36-2.jpg"},
        {"name": "Мужская корзина «Брутал»", "price": "12990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/whatsapp202023_10_1620v2014.38.08_14f00b4d_481x582.jpg"}
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # При старте просим телефон для бонусов (как было в начале)
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать в FruttoSmile!\n\nДля активации бонусной системы нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.contact.phone_number
    context.user_data['bonuses'] = 300
    await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов.")
    await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    await update.message.reply_text("Выберите действие:", reply_markup=kb)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_state = context.user_data.get('state')

    if msg == "⬅️ Назад":
        context.user_data['state'] = None
        await send_main_menu(update, context)
        return

    if msg == "📊 Информация о бонусах":
        b = context.user_data.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {b} бонусов.")

    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Иркутск, Улица Дыбовского, 8/5\n⏰ 09:00 - 20:00")

    elif msg == "🛒 Оформить заказ":
        kb = [[InlineKeyboardButton("🛍 Перейти на сайт", url="https://fruttosmile.ru")]]
        await update.message.reply_text("Заказы принимаем на сайте:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкое", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужское", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        links = [
            [InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/"),
             InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/")],
            [InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211"),
             InlineKeyboardButton("VK", url="https://vk.com/fruttosmile")]
        ]
        await update.message.reply_text("⭐ Пришлите скриншот отзыва для получения 250 бонусов!", 
                                        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))
        await update.message.reply_text("Площадки:", reply_markup=InlineKeyboardMarkup(links))

    elif msg == "📸 Получить фото заказа":
        context.user_data['state'] = 'WAIT_ORDER'
        btn = KeyboardButton("📲 Отправить мой номер", request_contact=True)
        await update.message.reply_text("Подтвердите номер для поиска заказа:", 
                                        reply_markup=ReplyKeyboardMarkup([[btn], ["⬅️ Назад"]], resize_keyboard=True))

    elif user_state == 'WAIT_ORDER':
        phone = update.message.text if update.message.text else update.message.contact.phone_number
        uid = update.message.from_user.id
        await update.message.reply_text(f"Ищу заказ по номеру {phone}... Менеджер скоро ответит!")
        admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Нет заказа", callback_data=f"no_order_{uid}")]])
        await context.bot.send_message(chat_id=ADMIN_ID, 
                                       text=f"🔔 ЗАПРОС ФОТО\n📱 Тел: {phone}\n🆔 ID: <code>{uid}</code>", 
                                       reply_markup=admin_kb, parse_mode="HTML")
        context.user_data['state'] = None

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("no_order_"):
        tid = int(query.data.replace("no_order_", ""))
        await context.bot.send_message(chat_id=tid, text="❌ Заказ не найден. Проверьте номер или напишите нам!")
    elif query.data.startswith("cat_"):
        cat = query.data.replace("cat_", "")
        prods = PRODUCTS.get(cat, [])
        await query.message.delete()
        for p in prods:
            await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 {p['price']}₽", parse_mode="HTML")
        await query.message.chat.send_message("Для возврата нажмите кнопку 'Назад'", reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid == ADMIN_ID and update.message.reply_to_message:
        try:
            tid = int(update.message.reply_to_message.text.split("🆔 ID: ")[1].strip())
            await context.bot.send_photo(chat_id=tid, photo=update.message.photo[-1].file_id, caption="Ваше фото заказа! ✨")
            await update.message.reply_text("✅ Отправлено!")
        except: await update.message.reply_text("Ошибка отправки.")
    elif context.user_data.get('state') == 'WAIT_REVIEW':
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                                     caption=f"📸 ОТЗЫВ от {update.message.from_user.full_name}")
        await update.message.reply_text("✅ Скриншот получен! Бонусы будут начислены после проверки.")
        context.user_data['state'] = None

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(query_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
