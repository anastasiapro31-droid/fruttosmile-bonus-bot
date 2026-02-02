import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q" # Замени на токен нового бота
ADMIN_ID = 1165444045  # Твой ID, который ты скинула

# Каталог товаров (пример заполнения)
PRODUCTS = {
    "sweet": [
        {"name": "Набор Клубники S", "price": "1600", "photo": "https://img.freepik.com/free-photo/chocolate-covered-strawberries_144627-7429.jpg"},
    ],
    "flowers": [
        {"name": "Букет с голубикой", "price": "3200", "photo": "https://img.freepik.com/free-photo/beautiful-flower-bouquet_23-2149053744.jpg"},
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт и регистрация"""
    contact_btn = KeyboardButton("📲 Стать участником программы лояльности", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "Добро пожаловать в Fruttosmile! 🍓✨\n\n"
        "За регистрацию мы начисляем вам 300 приветственных бонусов.\n"
        "Нажмите кнопку ниже, чтобы войти в личный кабинет:",
        reply_markup=keyboard
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """После регистрации"""
    context.user_data['phone'] = update.message.contact.phone_number
    context.user_data['bonuses'] = 300 
    await update.message.reply_text("🎉 Поздравляем! Вам начислено 300 приветственных бонусов Fruttosmile!")
    await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    keyboard = [
        ['📊 Информация о бонусах', '📍 Адреса самовывоза'],
        ['🛒 Оформить заказ', '📖 Каталог товаров'],
        ['📸 Получить фото заказа', '⭐ Оставить отзыв']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    text = "Вы в главном меню Fruttosmile! 🍓 Чем можем помочь?"
    
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    user_state = context.user_data.get('state')

    if msg == "⬅️ Назад":
        context.user_data['state'] = None
        await send_main_menu(update, context)
        return

    # МЕНЮ
    if msg == "📊 Информация о бонусах":
        bonuses = context.user_data.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {bonuses} бонусов.\n\nИспользуйте их для оплаты заказов!")

    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Мы ждем вас по адресу: Иркутск, Улица Дыбовского, 8/5\n⏰ Работаем каждый день с 09:00 до 20:00")

    elif msg == "🛒 Оформить заказ":
        kb = [[InlineKeyboardButton("🛍 Перейти на сайт", url="https://fruttosmile.ru")]]
        await update.message.reply_text("Оформить заказ можно на нашем сайте:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🍓 Клубника в шоколаде", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы и наборы", callback_data="cat_flowers")]
        ]
        await update.message.reply_text("Наш ассортимент:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        back_kb = ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        links = [
            [InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/?ll=104.353133%2C52.259946&z=14"), 
             InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/104.353179%2C52.259892")],
            [InlineKeyboardButton("Avito", url="https://www.avito.ru/brands/i190027211?ysclid=ml5c5ji39d797258865"), 
             InlineKeyboardButton("VK", url="https://vk.com/fruttosmile?ysclid=ml5b4zi1us569177487")]
        ]
        await update.message.reply_text("⭐ Оставьте отзыв и пришлите скриншот сюда для получения 250 бонусов!", reply_markup=back_kb)
        await update.message.reply_text("Выберите площадку:", reply_markup=InlineKeyboardMarkup(links))

    elif msg == "📸 Получить фото заказа":
        context.user_data['state'] = 'WAIT_ORDER_NUMBER'
        await update.message.reply_text("Введите номер вашего заказа:", reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))

    # ОБРАБОТКА НОМЕРА ЗАКАЗА
    elif user_state == 'WAIT_ORDER_NUMBER':
        phone = context.user_data.get('phone', 'Не указан')
        user_id = update.message.from_user.id
        await update.message.reply_text(f"Запрос по заказу №{msg} отправлен менеджеру. Ожидайте фото! ⏳")
        
        admin_kb = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Заказа не существует", callback_data=f"no_order_{user_id}")]])
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>ЗАПРОС ФОТО</b>\n📦 Заказ №: {msg}\n👤 Клиент: {update.message.from_user.full_name}\n📱 Тел: {phone}\n🆔 ID клиента: <code>{user_id}</code>",
            reply_markup=admin_kb,
            parse_mode="HTML"
        )
        context.user_data['state'] = None

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок от админа и каталога"""
    query = update.callback_query
    await query.answer()

    if query.data.startswith("no_order_"):
        target_id = int(query.data.replace("no_order_", ""))
        await context.bot.send_message(chat_id=target_id, text="❌ К сожалению, заказ с таким номером не найден. Пожалуйста, проверьте номер или оформите новый заказ! 🍓")
        await query.edit_message_text(text=query.message.text + "\n\n🚫 ОТМЕНЕНО: Заказ не найден")

    elif query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        products = PRODUCTS.get(category, [])
        await query.message.delete()
        for p in products:
            await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 Цена: {p['price']}₽", parse_mode="HTML")
        await query.message.chat.send_message("Для заказа вернитесь в меню.", reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка фото"""
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID and update.message.reply_to_message:
        try:
            target_id = int(update.message.reply_to_message.text.split("🆔 ID клиента: ")[1].strip())
            await context.bot.send_photo(chat_id=target_id, photo=update.message.photo[-1].file_id, caption="Ваше фото заказа от Fruttosmile! ✨")
            await update.message.reply_text("✅ Отправлено клиенту!")
        except:
            await update.message.reply_text("Ошибка отправки.")
    elif context.user_data.get('state') == 'WAIT_REVIEW':
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                                    caption=f"📸 Новый отзыв!\nКлиент: {update.message.from_user.full_name}")
        await update.message.reply_text("✅ Скриншот принят! Начислим бонусы после проверки.")
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
