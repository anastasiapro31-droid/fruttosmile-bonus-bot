import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q" 
ADMIN_ID = 1165444045 

PRODUCTS = {
    "boxes": [{"name": "Бенто-торт (8 ягод)", "price": "2490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"}, {"name": "Набор клубники и малины", "price": "2990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/06/malinki-takie-vecerinki.jpg"}],
    "flowers": [{"name": "Букет «Зефирка»", "price": "4490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"}],
    "sweet": [{"name": "Букет клубничный S", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"}],
    "meat": [{"name": "Букет «Мясной»", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"}]
}

# --- ФУНКЦИИ МЕНЮ ---
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    text = "Вы в главном меню FruttoSmile! 🍓"
    if update.message:
        await update.message.reply_text(text, reply_markup=kb)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать!\n\nДля активации бонусов и возможности запрашивать фото нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )

# --- ОБРАБОТКА КОНТАКТА ---
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.contact.phone_number
    uid = update.message.from_user.id
    
    # Если это первый раз (регистрация)
    if context.user_data.get('state') != 'WAIT_ORDER':
        context.user_data['phone'] = phone
        context.user_data['bonuses'] = 300
        await update.message.reply_text("🎉 Регистрация успешна! Вам начислено 300 бонусов.")
        await send_main_menu(update, context)
    else:
        # Если нажали "Получить фото заказа"
        await process_photo_request(update, context, phone)

async def process_photo_request(update: Update, context: ContextTypes.DEFAULT_TYPE, phone):
    uid = update.message.from_user.id
    await update.message.reply_text("🔍 Запрос отправлен менеджеру! Мы сообщим вам, когда статус изменится.")
    
    admin_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⏳ В работе", callback_data=f"st_work_{uid}"),
         InlineKeyboardButton("❌ Заказа нет", callback_data=f"st_none_{uid}")]
    ])
    
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 <b>ЗАПРОС ФОТО</b>\n\n📱 Тел: <code>{phone}</code>\n👤 Имя: {update.message.from_user.full_name}\n🆔 ID: <code>{uid}</code>\n\nОтветьте на это сообщение (Reply) фото-файлом.",
        reply_markup=admin_kb,
        parse_mode="HTML"
    )
    context.user_data['state'] = None

# --- ОБРАБОТКА ТЕКСТА ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    if msg == "⬅️ Назад":
        context.user_data['state'] = None
        await send_main_menu(update, context)
        return

    if msg == "📸 Получить фото заказа":
        context.user_data['state'] = 'WAIT_ORDER'
        if 'phone' in context.user_data:
            await process_photo_request(update, context, context.user_data['phone'])
        else:
            btn = KeyboardButton("📲 Подтвердить мой номер", request_contact=True)
            await update.message.reply_text("Для поиска заказа подтвердите ваш номер:", 
                                            reply_markup=ReplyKeyboardMarkup([[btn], ["⬅️ Назад"]], resize_keyboard=True))

    elif msg == "📊 Информация о бонусах":
        b = context.user_data.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {b} бонусов.")
    elif msg == "📖 Каталог товаров":
        kb = [[InlineKeyboardButton("🎁 Боксы", callback_data="cat_boxes")], [InlineKeyboardButton("🍓 Сладкое", callback_data="cat_sweet")]]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))
    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Иркутск, Улица Дыбовского, 8/5")
    elif msg == "🛒 Оформить заказ":
        await update.message.reply_text("Сайт: https://fruttosmile.ru")

# --- CALLBACK И ФОТО ---
async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data.startswith("st_"):
        uid = int(query.data.split("_")[2])
        msg = "⏳ Ваш заказ в работе! Менеджер скоро свяжется с вами." if "work" in query.data else "❌ Заказ на этот номер не найден."
        await context.bot.send_message(chat_id=uid, text=msg)
        await query.edit_message_text(text=query.message.text + f"\n\n✅ Статус обновлен")
    elif query.data.startswith("cat_"):
        cat = query.data.replace("cat_", "")
        for p in PRODUCTS.get(cat, []):
            await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 {p['price']}₽", parse_mode="HTML")

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id == ADMIN_ID and update.message.reply_to_message:
        try:
            target_id = int(update.message.reply_to_message.text.split("🆔 ID: ")[1].strip())
            await context.bot.send_photo(chat_id=target_id, photo=update.message.photo[-1].file_id, caption="📸 Ваш заказ готов! Менеджер прислал фото.")
            await update.message.reply_text("✅ Отправлено клиенту!")
        except: await update.message.reply_text("Ошибка отправки.")

# --- ЗАПУСК ---
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
