import telebot
import time
import threading
import os
import json
import requests
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

load_dotenv()

# ============= ОСНОВНЫЕ НАСТРОЙКИ =============
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YOUR_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 30))
SETTINGS_FILE = "settings.json"

if not all([TELEGRAM_TOKEN, YOUR_CHAT_ID]):
    print("❌ Ошибка! Проверьте файл .env.")
    exit(1)

bot = telebot.TeleBot(TELEGRAM_TOKEN)

DEFAULT_SETTINGS = {
    "BTC-USDT": {"lower": 50000.0, "upper": 70000.0}
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Ошибка чтения settings.json, используются настройки по умолчанию.")
                return DEFAULT_SETTINGS.copy()
    else:
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)

settings = load_settings()
alert_sent = {pair: {"lower": False, "upper": False} for pair in settings.keys()}

def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    keyboard.add(
        KeyboardButton("💰 Цены"),
        KeyboardButton("📊 Статус"),
        KeyboardButton("➕ Добавить пару"),
        KeyboardButton("❌ Удалить пару"),
        KeyboardButton("📝 Помощь"),
        KeyboardButton("🔒 Скрыть меню")
    )
    return keyboard

def symbol_is_valid(symbol):
    try:
        url = f"https://open-api.bingx.com/openApi/swap/v2/quote/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        return data.get('code') == 0
    except:
        return False

def get_current_price(symbol):
    try:
        url = f"https://open-api.bingx.com/openApi/swap/v2/quote/price?symbol={symbol}"
        response = requests.get(url, timeout=10)
        data = response.json()
        if data.get('code') == 0:
            return float(data['data']['price'])
        else:
            print(f"Ошибка API BingX ({symbol}): {data.get('msg')}")
            return None
    except Exception as e:
        print(f"Ошибка при получении цены {symbol}: {e}")
        return None

def send_telegram_message(message):
    try:
        bot.send_message(YOUR_CHAT_ID, message)
        print(f"✅ Сообщение отправлено")
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")

# ============= ОБНОВЛЁННАЯ ФУНКЦИЯ МОНИТОРИНГА =============
def check_all_prices():
    for pair, cfg in settings.items():
        price = get_current_price(pair)
        if price is None:
            continue
        print(f"[{time.strftime('%H:%M:%S')}] {pair}: ${price:,.2f}")

        lower = cfg["lower"]
        upper = cfg["upper"]

        # Нижняя граница
        if price < lower:
            if not alert_sent[pair]["lower"]:
                msg = (f"🔴 ВНИМАНИЕ! ЦЕНА УПАЛА!\n\n"
                       f"Актив: {pair}\n"
                       f"Нижняя граница: ${lower:,.2f}\n"
                       f"Текущая цена: ${price:,.2f}\n"
                       f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                send_telegram_message(msg)
                alert_sent[pair]["lower"] = True
        else:
            if alert_sent[pair]["lower"]:
                msg = (f"✅ ЦЕНА ВЕРНУЛАСЬ В ДИАПАЗОН!\n\n"
                       f"Актив: {pair}\n"
                       f"Нижняя граница: ${lower:,.2f}\n"
                       f"Текущая цена: ${price:,.2f}\n"
                       f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                send_telegram_message(msg)
                alert_sent[pair]["lower"] = False

        # Верхняя граница
        if price > upper:
            if not alert_sent[pair]["upper"]:
                msg = (f"🟢 ВНИМАНИЕ! ЦЕНА ПОДНЯЛАСЬ!\n\n"
                       f"Актив: {pair}\n"
                       f"Верхняя граница: ${upper:,.2f}\n"
                       f"Текущая цена: ${price:,.2f}\n"
                       f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                send_telegram_message(msg)
                alert_sent[pair]["upper"] = True
        else:
            if alert_sent[pair]["upper"]:
                msg = (f"✅ ЦЕНА ВЕРНУЛАСЬ В ДИАПАЗОН!\n\n"
                       f"Актив: {pair}\n"
                       f"Верхняя граница: ${upper:,.2f}\n"
                       f"Текущая цена: ${price:,.2f}\n"
                       f"Время: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                send_telegram_message(msg)
                alert_sent[pair]["upper"] = False

def start_monitoring():
    print("=" * 50)
    print("🚀 БОТ ЗАПУЩЕН")
    print("=" * 50)
    print(f"Отслеживаемые пары: {', '.join(settings.keys())}")
    print(f"⏱️  Проверка каждые {CHECK_INTERVAL} секунд")
    print("=" * 50)
    print("Ожидание изменения цены...\n")
    while True:
        check_all_prices()
        time.sleep(CHECK_INTERVAL)

# ============= ОБРАБОТЧИКИ КОМАНД =============
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,
                     "👋 Привет! Я бот для отслеживания цен криптовалют.\n\n"
                     "Используй кнопки меню или текстовые команды:\n"
                     "/prices — текущие цены\n"
                     "/status — текущие границы\n"
                     "/set_range <символ> <нижняя> <верхняя> — установить диапазон\n"
                     "/set_lower <символ> <нижняя> — нижнюю границу\n"
                     "/set_upper <символ> <верхняя> — верхнюю границу\n"
                     "/add_pair <символ> — добавить пару\n"
                     "/remove_pair <символ> — удалить пару\n"
                     "/help — полная справка\n"
                     "/hide — убрать клавиатуру",
                     reply_markup=main_menu_keyboard())

@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "📖 *Полная справка по командам:*\n\n"
        "`/prices` – показать текущие цены всех пар\n"
        "`/status` – показать установленные границы\n"
        "`/set_range <символ> <нижняя> <верхняя>` – установить диапазон (пример: `/set_range BTC-USDT 50000 70000`)\n"
        "`/set_lower <символ> <нижняя>` – установить только нижнюю границу\n"
        "`/set_upper <символ> <верхняя>` – установить только верхнюю границу\n"
        "`/add_pair <символ>` – добавить новую пару (проверка доступности)\n"
        "`/remove_pair <символ>` – удалить пару из отслеживания\n"
        "`/start` – показать меню и приветствие\n"
        "`/help` – эта справка\n"
        "`/hide` – убрать клавиатуру\n\n"
        "Для удобства используйте кнопки меню."
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")

@bot.message_handler(commands=['hide'])
def hide_keyboard(message):
    hide_markup = ReplyKeyboardMarkup(remove_keyboard=True)
    bot.send_message(message.chat.id, "Клавиатура скрыта. Чтобы вернуть, введите /start", reply_markup=hide_markup)

@bot.message_handler(commands=['prices'])
def send_prices(message):
    lines = []
    for pair in settings.keys():
        price = get_current_price(pair)
        if price is None:
            lines.append(f"❌ {pair}: ошибка получения цены")
        else:
            lines.append(f" {pair}: ${price:,.2f}")
    bot.reply_to(message, "\n".join(lines))

@bot.message_handler(commands=['status'])
def send_status(message):
    lines = ["📊 Текущие настройки:"]
    for pair, cfg in settings.items():
        lines.append(f"{pair}: нижняя ${cfg['lower']:,.2f}, верхняя ${cfg['upper']:,.2f}")
    bot.reply_to(message, "\n".join(lines))

def update_env_var(key, value):
    env_file = ".env"
    lines = []
    found = False
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
    with open(env_file, "w") as f:
        for line in lines:
            if line.startswith(f"{key}="):
                f.write(f"{key}={value}\n")
                found = True
            else:
                f.write(line)
        if not found:
            f.write(f"{key}={value}\n")
    load_dotenv(override=True)

@bot.message_handler(commands=['set_range'])
def set_range(message):
    try:
        parts = message.text.split()
        if len(parts) != 4:
            bot.reply_to(message, "Использование: /set_range <символ> <нижняя> <верхняя>\nПример: /set_range BTC-USDT 50000 70000")
            return
        symbol = parts[1].upper()
        lower = float(parts[2])
        upper = float(parts[3])
        if lower <= 0 or upper <= 0:
            bot.reply_to(message, "Границы должны быть положительными числами.")
            return
        if lower >= upper:
            bot.reply_to(message, "Нижняя граница должна быть меньше верхней.")
            return
        if symbol not in settings:
            bot.reply_to(message, f"Пара {symbol} не отслеживается. Добавьте её командой /add_pair {symbol}")
            return
        settings[symbol]["lower"] = lower
        settings[symbol]["upper"] = upper
        save_settings(settings)
        if symbol in alert_sent:
            alert_sent[symbol]["lower"] = False
            alert_sent[symbol]["upper"] = False
        bot.reply_to(message, f"✅ Диапазон для {symbol} установлен:\n📉 Нижняя: ${lower:,.2f}\n📈 Верхняя: ${upper:,.2f}")
    except ValueError:
        bot.reply_to(message, "Ошибка: введите числа, например /set_range BTC-USDT 50000 70000")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['set_lower'])
def set_lower(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Использование: /set_lower <символ> <нижняя>\nПример: /set_lower BTC-USDT 50000")
            return
        symbol = parts[1].upper()
        lower = float(parts[2])
        if lower <= 0:
            bot.reply_to(message, "Нижняя граница должна быть положительным числом.")
            return
        if symbol not in settings:
            bot.reply_to(message, f"Пара {symbol} не отслеживается.")
            return
        settings[symbol]["lower"] = lower
        save_settings(settings)
        if symbol in alert_sent:
            alert_sent[symbol]["lower"] = False
        bot.reply_to(message, f"✅ Нижняя граница для {symbol}: ${lower:,.2f}")
    except ValueError:
        bot.reply_to(message, "Ошибка: введите число, например /set_lower BTC-USDT 50000")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['set_upper'])
def set_upper(message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "Использование: /set_upper <символ> <верхняя>\nПример: /set_upper BTC-USDT 70000")
            return
        symbol = parts[1].upper()
        upper = float(parts[2])
        if upper <= 0:
            bot.reply_to(message, "Верхняя граница должна быть положительным числом.")
            return
        if symbol not in settings:
            bot.reply_to(message, f"Пара {symbol} не отслеживается.")
            return
        settings[symbol]["upper"] = upper
        save_settings(settings)
        if symbol in alert_sent:
            alert_sent[symbol]["upper"] = False
        bot.reply_to(message, f"✅ Верхняя граница для {symbol}: ${upper:,.2f}")
    except ValueError:
        bot.reply_to(message, "Ошибка: введите число, например /set_upper BTC-USDT 70000")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['add_pair'])
def add_pair(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Использование: /add_pair <символ>\nПример: /add_pair XRP-USDT")
            return
        symbol = parts[1].upper()
        if symbol in settings:
            bot.reply_to(message, f"Пара {symbol} уже отслеживается.")
            return
        if not symbol_is_valid(symbol):
            bot.reply_to(message, f"❌ Пара {symbol} не найдена на BingX. Проверьте формат (например, BTC-USDT).")
            return
        settings[symbol] = {"lower": 0.0, "upper": 0.0}
        alert_sent[symbol] = {"lower": False, "upper": False}
        save_settings(settings)
        bot.reply_to(message, f"✅ Пара {symbol} добавлена. Установите границы командами /set_lower и /set_upper.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(commands=['remove_pair'])
def remove_pair(message):
    try:
        parts = message.text.split()
        if len(parts) != 2:
            bot.reply_to(message, "Использование: /remove_pair <символ>\nПример: /remove_pair XRP-USDT")
            return
        symbol = parts[1].upper()
        if symbol not in settings:
            bot.reply_to(message, f"Пара {symbol} не отслеживается.")
            return
        del settings[symbol]
        if symbol in alert_sent:
            del alert_sent[symbol]
        save_settings(settings)
        bot.reply_to(message, f"✅ Пара {symbol} удалена из отслеживания.")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    text = message.text
    if text == "💰 Цены":
        send_prices(message)
    elif text == "📊 Статус":
        send_status(message)
    elif text == "➕ Добавить пару":
        bot.reply_to(message, "Введите /add_pair <символ>\nПример: /add_pair XRP-USDT")
    elif text == "❌ Удалить пару":
        bot.reply_to(message, "Введите /remove_pair <символ>\nПример: /remove_pair SOL-USDT")
    elif text == "📝 Помощь":
        send_help(message)
    elif text == "🔒 Скрыть меню":
        hide_keyboard(message)

# ============= ЗАПУСК =============
if __name__ == "__main__":
    lines = ["🤖 Бот запущен!\nОтслеживаемые пары:"]
    for pair in settings.keys():
        cfg = settings[pair]
        lines.append(f"{pair}: ${cfg['lower']:,.2f} – ${cfg['upper']:,.2f}")
    send_telegram_message("\n".join(lines))

    monitor_thread = threading.Thread(target=start_monitoring, daemon=True)
    monitor_thread.start()

    try:
        bot.get_updates(offset=-1, timeout=5)
        print("Сброс offset выполнен")
    except Exception as e:
        print(f"Сброс offset не удался: {e}")

    print("Telegram бот готов. Нажмите Ctrl+C для остановки")
    bot.infinity_polling(skip_pending=True, timeout=30)