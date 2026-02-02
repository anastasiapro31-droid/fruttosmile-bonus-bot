import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q"
ADMIN_ID = 1165444045  # Твой цифровой ID (узнай в @userinfobot)

# Каталог товаров Fruttosmile (только просмотр)
PRODUCTS = {
    "sweet": [
        {"name": "Клубника в шоколаде S", "price": "1600", "photo": "https://clck.ru/388zzz"},
        {"name": "Набор Mix Gold", "price": "2500", "photo": "https://clck.ru/388yyy"},
    ],
    "flowers": [
        {"name": "Букет с голубикой", "price": "3200", "photo": "https://clck.ru/388xxx"},
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и регистрация в Fruttosmile"""
    contact_btn = KeyboardButton("📲 Стать участником программы лояльности", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_btn]], resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "Добро пожаловать в Fruttosmile! 🍓✨\n\n"
        "За регистрацию в нашей программе лояльности мы начисляем приветственные бонусы.\n"
        "Нажмите кнопку ниже, чтобы подтвердить номер и войти:",
        reply_markup=keyboard
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """После получения контакта открываем меню"""
    context.user_data['phone'] = update.message.contact.phone_number
    await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню Fruttosmile"""
    keyboard = [
        ['📊 Информация о бонусах', '📍 Адреса самовывоза'],
        ['🛒 Оформить заказ', '📖 Каталог товаров'],
        ['📸 Получить фото заказа', '⭐ Оставить отзыв']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    text = "Вы успешно вошли в программу лояльности Fruttosmile! 🎁"
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup)
    else:
        await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text

    if msg == "🛒 Оформить заказ":
        # Ссылка сразу на ваш сайт или WhatsApp
        kb = [[InlineKeyboardButton("🛍 Перейти к заказу", url="https://fruttosmile.ru")]]
        await update.message.reply_text(
            "Для оформления заказа переходите на наш сайт.\nТам можно выбрать удобное время доставки!",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🍓 Клубника в шоколаде", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы и наборы", callback_data="cat_flowers")]
        ]
        await update.message.reply_text("Посмотрите наш актуальный ассортимент:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        kb = [
            [InlineKeyboardButton("Яндекс", url="ССЫЛКА"), InlineKeyboardButton("2ГИС", url="ССЫЛКА")],
            [InlineKeyboardButton("Google", url="ССЫЛКА"), InlineKeyboardButton("VK", url="ССЫЛКА")]
        ]
        await update.message.reply_text(
            "⭐ Оставьте отзыв о Fruttosmile на любой площадке и пришлите скриншот сюда.\n\n"
            "После модерации мы начислим вам 250 бонусов! 📸",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Мы ждем вас по адресу: [Ваш адрес здесь]\n⏰ Работаем каждый день с 09:00 до 21:00")

    elif msg == "📊 Информация о бонусах":
        await update.message.reply_text("🎁 Ваш баланс в Fruttosmile: 0 бонусов\n(Бонусы станут доступны после проверки ваших отзывов)")

    elif msg == "⬅️ Назад в меню":
        await send_main_menu(update, context)

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылка скриншота админу Fruttosmile"""
    if context.user_data.get('state') == 'WAIT_REVIEW':
        phone = context.user_data.get('phone', 'Не указан')
        name = update.message.from_user.full_name
        
        await update.message.reply_text("✅ Скриншот принят! Скоро мы проверим его и начислим бонусы.")
        
        # Отправляем фото тебе
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=update.message.photo[-1].file_id,
            caption=f"📸 <b>Новый отзыв Fruttosmile!</b>\n👤 Клиент: {name}\n📱 Тел: {phone}",
            parse_mode="HTML"
        )
        context.user_data['state'] = None

async def cat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ карточек товаров без возможности купить в боте"""
    query = update.callback_query
    await query.answer()
    category = query.data.replace("cat_", "")
    
    products = PRODUCTS.get(category, [])
    await query.message.delete()

    for p in products:
        caption = f"<b>{p['name']}</b>\n💰 Цена: {p['price']}₽"
        if p.get('photo'):
            await query.message.chat.send_photo(photo=p['photo'], caption=caption, parse_mode="HTML")
        else:
            await query.message.chat.send_message(caption, parse_mode="HTML")

    back_kb = [['⬅️ Назад в меню']]
    await query.message.chat.send_message("Для оформления заказа используйте кнопку в главном меню.", 
                                          reply_markup=ReplyKeyboardMarkup(back_kb, resize_keyboard=True))

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(CallbackQueryHandler(cat_handler, pattern="^cat_"))
    
    print("Бот Fruttosmile запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()
