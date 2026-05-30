import telebot
from telebot import types
import logging
import html

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8799157488:AAGyd29t4Ip3dK5AnY2O5gJWCPXMKkgaAwg"  # Рабочий токен бота
ADMIN_CHAT_ID = -1003897470783  # ID канала брата
# ------------------

bot = telebot.TeleBot(BOT_TOKEN)
logging.basicConfig(level=logging.INFO)

# Временное хранилище для активных заявок
user_requests = {}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_payout = types.KeyboardButton("💰 Получить выплату за промокод")
    btn_profile = types.KeyboardButton("👤 Личный кабинет")
    btn_support = types.KeyboardButton("🆘 Поддержка")
    markup.add(btn_payout)
    markup.add(btn_profile, btn_support)
    return markup

@bot.message_handler(commands=['start'])
def start_cmd(message):
    bot.send_message(
        message.chat.id, 
        f"Привет, {message.from_user.first_name}! Добро пожаловать в бот выплат. Воспользуйся меню ниже:",
        reply_markup=get_main_keyboard()
    )

# --- ОБРАБОТКА ОТВЕТОВ ИЗ КАНАЛА ---
@bot.channel_post_handler(func=lambda message: message.reply_to_message is not None)
def handle_admin_reply(message):
    if message.chat.id != ADMIN_CHAT_ID:
        return

    original_text = message.reply_to_message.caption or message.reply_to_message.text
    if not original_text or "User_ID:" not in original_text:
        return

    try:
        # Умный поиск ID (извлекает только цифры после двоеточия)
        raw_part = original_text.split("User_ID:")[1]
        clean_id = "".join(c for c in raw_part if c.isdigit())
        
        user_id = int(clean_id)
        
        if "Новый вопрос в поддержку!" in original_text:
            response_text = f"📢 <b>Ответ от поддержки:</b>\n\n{html.escape(message.text)}"
        else:
            response_text = f"📢 <b>Ответ по вашей заявке:</b>\n\n{html.escape(message.text)}"

        bot.send_message(chat_id=user_id, text=response_text, parse_mode="HTML")
        bot.send_message(ADMIN_CHAT_ID, f"✅ Ответ успешно отправлен игроку (ID: {user_id})", reply_markup=None)
    except Exception as e:
        bot.send_message(ADMIN_CHAT_ID, f"❌ Не удалось отправить ответ: {e}")

# --- ГЛАВНОЕ МЕНЮ ---
@bot.message_handler(func=lambda message: True)
def handle_menu(message):
    if message.text == "💰 Получить выплату за промокод":
        user_requests[message.chat.id] = {}
        msg = bot.send_message(
            message.chat.id, 
            "<b>Шаг 1 из 3</b>\n\nОтправьте скриншот момента, как вы ввели промокод (из окна F2, где чётко видно, какой промокод был введён).\n\nПожалуйста, отправьте как изображение, а не файлом:", 
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )
        bot.register_next_step_handler(msg, process_step_screenshot)

    elif message.text == "👤 Личный кабинет":
        username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
        text = (
            f"👤 <b>Ваш Личный Кабинет</b>\n\n"
            f"
