import telebot
from telebot import types
import logging
import html

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8799157488:AAGyd29t4Ip3dK5AnY2O5gJWCPXMKkgaAwg"  # Токен бота
ADMIN_CHAT_ID = -1003897470783  # ID канала брата
# ------------------

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# Временное хранилище данных
user_requests = {}

# --- КЛАВИАТУРЫ ---
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_payout = types.KeyboardButton("💰 Оформить выплату")
    btn_profile = types.KeyboardButton("👤 Мой профиль")
    btn_support = types.KeyboardButton("🆘 Связь с админом")
    markup.add(btn_payout)
    markup.add(btn_profile, btn_support)
    return markup

def get_cancel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_cancel = types.KeyboardButton("🔙 Назад в меню")
    markup.add(btn_cancel)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    welcome_text = (
        f"Привет, {message.from_user.first_name}!\n\n"
        f"Через этого бота можно получить деньги за введённый промокод на проекте RMRP. "
        f"Выбирай нужный раздел в меню ниже:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

# --- ОБРАБОТКА ОТВЕТОВ ИЗ КАНАЛА ---
@bot.channel_post_handler(func=lambda message: message.reply_to_message is not None)
def handle_admin_reply(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    original_text = message.reply_to_message.caption or message.reply_to_message.text
    if not original_text or "User_ID:" not in original_text:
        return

    try:
        raw_part = original_text.split("User_ID:")[1]
        clean_id = "".join(c for c in raw_part if c.isdigit())
        user_id = int(clean_id)
        
        if "Поступило новое обращение!" in original_text:
            response_text = f"✉️ <b>Ответ от администрации:</b>\n\n{html.escape(message.text)}"
        else:
            response_text = f"💵 <b>Новости по выплате:</b>\n\n{html.escape(message.text)}"

        bot.send_message(chat_id=user_id, text=response_text, parse_mode="HTML")
        bot.send_message(ADMIN_CHAT_ID, f"✅ Ответ отправлен (ID: {user_id})", reply_markup=None)
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Ошибка отправки: {e}")

# --- ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "🔙 Назад в меню":
        if message.chat.id in user_requests:
            del user_requests[message.chat.id]
        bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard())
        return

    if message.text == "💰 Оформить выплату":
        user_requests[message.chat.id] = {}
        msg = bot.send_message(
            message.chat.id, 
            "<b>Шаг 1 из 3: Скриншот</b>\n\n"
            "Сделай скриншот, чтобы было видно активацию промокода на RMRP.\n\n"
            "<i>Отправь его как обычную картинку (не файлом):</i>", 
            parse_mode="HTML",
            reply_markup=get_cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_step_screenshot)

    elif message.text == "👤 Мой профиль":
        username = f"@{message.from_user.username}" if message.from_user.username else "нет"
        text = (
            f"📋 <b>Твой аккаунт:</b>\n\n"
            f"• Имя: {html.escape(message.from_user.full_name)}\n"
            f"• Юзернейм: {html.escape(username)}\n"
            f"• Твой ID: <code>{message.chat.id}</code>"
        )
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=get_main_keyboard())

    elif message.text == "🆘 Связь с админом":
        msg = bot.send_message(
            message.chat.id, 
            "<b>Напиши свой вопрос:</b>\n\n"
            "Напиши всё одним сообщением, и админ тебе обязательно ответит.",
            reply_markup=get_cancel_keyboard()
        )
        bot.register_next_step_handler(msg, process_support_question)

# --- ШАГИ ЗАЯВКИ НА ВЫПЛАТУ ---
def process_step_screenshot(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.photo:
        msg = bot.send_message(message.chat.id, "⚠️ Это не картинка. Скинь именно скриншот:")
        bot.register_next_step_handler(msg, process_step_screenshot)
        return

    user_requests[message.chat.id]['photo_id'] = message.photo[-1].file_id

    msg = bot.send_message(
        message.chat.id, 
        "<b>Шаг 2 из 3: Номер счёта</b>\n\n"
        "Напиши номер своего банковского счёта на сервере RMRP:",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_bank)

def process_step_bank(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Напиши счёт обычным текстом:")
        bot.register_next_step_handler(msg, process_step_bank)
        return

    user_requests[message.chat.id]['bank'] = message.text

    msg = bot.send_message(
        message.chat.id, 
        "<b>Шаг 3 из 3: Сервер</b>\n\n"
        "На каком сервере RMRP ты играешь? (если он один, просто напиши название или укажи 'основной'):",
        parse_mode="HTML"
    )
    bot.register_next_step_handler(msg, process_step_server)

def process_step_server(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "⚠️ Напиши название сервера текстом:")
        bot.register_next_step_handler(msg, process_step_server)
        return

    user_requests[message.chat.id]['server'] = message.text

    req_data = user_requests[message.chat.id]
    username = f"@{message.from_user.username}" if message.from_user.username else "нет"

    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_server = html.escape(req_data['server'])
    safe_bank = html.escape(req_data['bank'])

    admin_text = (
        f"📊 <b>Зарегистрирована новая анкета на выплату!</b>\n\n"
        f"• <b>Пользователь:</b> {safe_name} ({safe_username})\n"
        f"• <b>Игровой сервер RMRP:</b> {safe_server}\n"
        f"• <b>Реквизиты банка:</b> <code>{safe_bank}</code>\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    try:
        bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=req_data['photo_id'], caption=admin_text, parse_mode="HTML")
        bot.send_message(
            message.chat.id, 
            "✅ Данные приняты! Анкета отправлена админам на проверку. Жди выплату.", 
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при отправке. Напиши в поддержку. ({e})", reply_markup=get_main_keyboard())
    
    if message.chat.id in user_requests:
        del user_requests[message.chat.id]

# --- ПОДДЕРЖКА ---
def process_support_question(message):
    if message.text == "🔙 Назад в меню" or message.text in ["💰 Оформить выплату", "👤 Мой профиль", "🆘 Связь с админом"]:
        handle_menu(message)
        return

    if not message.text:
        msg = bot.send_message(message.chat.id, "Напиши свой вопрос текстом:")
        bot.register_next_step_handler(msg, process_support_question)
        return

    username = f"@{message.from_user.username}" if message.from_user.username else "нет"
    
    safe_name = html.escape(message.from_user.full_name)
    safe_username = html.escape(username)
    safe_question = html.escape(message.text)

    admin_text = (
        f"📬 <b>Поступило новое обращение!</b>\n\n"
        f"• <b>Отправитель:</b> {safe_name} ({safe_username})\n"
        f"• <b>Суть вопроса:</b> {safe_question}\n\n"
        f"User_ID: <code>{message.chat.id}</code>"
    )

    bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text, parse_mode="HTML")
    bot.send_message(
        message.chat.id, 
        "Твой вопрос отправлен. Ответ придёт прямо сюда.", 
        reply_markup=get_main_keyboard()
    )

if __name__ == '__main__':
    print("Бот успешно запущен со встроенным меню...")
    bot.infinity_polling()
