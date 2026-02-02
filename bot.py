import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8589427171:AAEZ2J3Eug-ynLUuGZlM4ByYeY-sGWjFe2Q" # Замени на свой токен
ADMIN_ID = 1165444045 

PRODUCTS = {
    "boxes": [
        {"name": "Бенто-торт из клубники (8 ягод)", "price": "2490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/07/photoeditorsdk-export4.png"},
        {"name": "Набор клубники и малины в шоколаде", "price": "2990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/06/malinki-takie-vecerinki.jpg"},
        {"name": "Бокс «С надписью» Средний", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/boks-s-nadpisyu.jpg"}
    ],
    "flowers": [
        {"name": "Букет «Зефирка»", "price": "4490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/03/photoeditorsdk_export_37__481x582.png"},
        {"name": "Букет из роз и эустомы", "price": "3490", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-iz-roz-i-eustomy.jpg"}
    ],
    "sweet": [
        {"name": "Букет клубничный S Ажурный", "price": "3990", "photo": "http://fruttosmile.su/wp-content/uploads/2025/02/buket-klubnichnyj-s-azhurnyj-1.jpg"},
        {"name": "Букет «Ягодное ассорти»", "price": "6490", "photo": "http://fruttosmile.su/wp-content/uploads/2016/12/photo_2024-04-05_17-55-09.jpg"}
    ],
    "meat": [
        {"name": "Букет «Мясной» стандарт", "price": "5990", "photo": "http://fruttosmile.su/wp-content/uploads/2017/02/photo_2024-08-08_16-52-24.jpg"}
    ]
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    btn = KeyboardButton("📲 Регистрация и +300 бонусов", request_contact=True)
    await update.message.reply_text(
        "🍓 Добро пожаловать в FruttoSmile!\n\nДля активации бонусной системы и возможности запрашивать фото нажмите кнопку ниже 👇",
        reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True, one_time_keyboard=True)
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['phone'] = update.message.contact.phone_number
    context.user_data['bonuses'] = 300
    await update.message.reply_text("🎉 Регистрация успешна! Теперь вы можете пользоваться всеми функциями бота.")
    await send_main_menu(update, context)

async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = ReplyKeyboardMarkup([
        ["📊 Информация о бонусах", "📖 Каталог товаров"],
        ["🛒 Оформить заказ", "📸 Получить фото заказа"],
        ["⭐ Оставить отзыв", "📍 Адреса самовывоза"]
    ], resize_keyboard=True)
    await update.message.reply_text("Главное меню:", reply_markup=kb)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    uid = update.message.from_user.id
    phone = context.user_data.get('phone')

    if msg == "⬅️ Назад":
        context.user_data['state'] = None
        await send_main_menu(update, context)
        return

    if msg == "📊 Информация о бонусах":
        b = context.user_data.get('bonuses', 0)
        await update.message.reply_text(f"🎁 Ваш баланс: {b} бонусов.")

    elif msg == "📍 Адреса самовывоза":
        await update.message.reply_text("📍 Мы ждем вас: Иркутск, Улица Дыбовского, 8/5\n⏰ Ежедневно с 09:00 до 20:00")

    elif msg == "🛒 Оформить заказ":
        kb = [[InlineKeyboardButton("🛍 Перейти на сайт", url="https://fruttosmile.ru")]]
        await update.message.reply_text("Оформить заказ можно на сайте:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📖 Каталог товаров":
        kb = [
            [InlineKeyboardButton("🎁 Подарочные боксы", callback_data="cat_boxes")],
            [InlineKeyboardButton("🍓 Сладкие заказы", callback_data="cat_sweet")],
            [InlineKeyboardButton("💐 Цветы", callback_data="cat_flowers")],
            [InlineKeyboardButton("🍖 Мужские заказы", callback_data="cat_meat")]
        ]
        await update.message.reply_text("Выберите категорию:", reply_markup=InlineKeyboardMarkup(kb))

    elif msg == "📸 Получить фото заказа":
        if not phone:
            btn = KeyboardButton("📲 Поделиться номером", request_contact=True)
            await update.message.reply_text("Сначала поделитесь номером телефона для поиска:", 
                                            reply_markup=ReplyKeyboardMarkup([[btn]], resize_keyboard=True))
            return

        await update.message.reply_text("🔍 Запрос отправлен менеджеру! Мы сообщим вам, как только статус заказа изменится.")
        
        admin_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ В работе", callback_data=f"st_work_{uid}"),
             InlineKeyboardButton("❌ Заказа нет", callback_data=f"st_none_{uid}")]
        ])
        
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(f"🔔 <b>ЗАПРОС ФОТО</b>\n\n"
                  f"📱 Тел: <code>{phone}</code>\n"
                  f"👤 Имя: {update.message.from_user.full_name}\n"
                  f"🆔 ID: <code>{uid}</code>\n\n"
                  f"Чтобы отправить фото, ответьте на это сообщение (Reply) картинкой."),
            reply_markup=admin_kb,
            parse_mode="HTML"
        )

    elif msg == "⭐ Оставить отзыв":
        context.user_data['state'] = 'WAIT_REVIEW'
        links = [[InlineKeyboardButton("Яндекс", url="https://yandex.ru/maps/org/fruttosmile/58246506027/"), 
                  InlineKeyboardButton("2ГИС", url="https://2gis.ru/irkutsk/firm/1548641653278292/")]]
        await update.message.reply_text("⭐ Пришлите скриншот отзыва для начисления 250 бонусов!", 
                                        reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))
        await update.message.reply_text("Где оставить отзыв:", reply_markup=InlineKeyboardMarkup(links))

async def query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("st_"):
        uid = int(query.data.split("_")[2])
        if "work" in query.data:
            await context.bot.send_message(chat_id=uid, text="⏳ Ваш заказ сейчас в работе! Менеджер скоро свяжется с вами.")
            await query.edit_message_text(text=query.message.text + "\n\n✅ ОТВЕТ: В работе")
        elif "none" in query.data:
            await context.bot.send_message(chat_id=uid, text="❌ К сожалению, заказ на данный номер не найден.")
            await query.edit_message_text(text=query.message.text + "\n\n✅ ОТВЕТ: Не найден")

    elif query.data.startswith("cat_"):
        cat = query.data.replace("cat_", "")
        prods = PRODUCTS.get(cat, [])
        await query.message.delete()
        for p in prods:
            await query.message.chat.send_photo(photo=p['photo'], caption=f"<b>{p['name']}</b>\n💰 {p['price']}₽", parse_mode="HTML")
        await query.message.chat.send_message("Для возврата в меню нажмите кнопку 'Назад'", 
                                              reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True))

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    # Если админ отвечает на сообщение с запросом фото
    if uid == ADMIN_ID and update.message.reply_to_message:
        try:
            target_id = int(update.message.reply_to_message.text.split("🆔 ID: ")[1].strip())
            await context.bot.send_photo(chat_id=target_id, photo=update.message.photo[-1].file_id, 
                                         caption="📸 Ваш заказ готов! Менеджер прислал фото вашего заказа. ✨")
            await update.message.reply_text("✅ Фото заказа успешно доставлено клиенту!")
        except:
            await update.message.reply_text("Ошибка: не удалось найти ID клиента в сообщении.")
    # Если клиент шлет отзыв
    elif context.user_data.get('state') == 'WAIT_REVIEW':
        await context.bot.send_photo(chat_id=ADMIN_ID, photo=update.message.photo[-1].file_id, 
                                     caption=f"📸 ОТЗЫВ от {update.message.from_user.full_name}")
        await update.message.reply_text("✅ Скриншот принят! Менеджер начислит бонусы после проверки.")
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
