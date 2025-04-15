import random
import asyncio
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters

# Настройки
TOKEN = '8145291232:AAHXl2K77zhKk0cemoLpPsVjETcxRNDksVY'  # Токен бота
SECRET_CODE = "111111"
EMOJI_LIST = ["💀", "❤️", "😭", "✅"]
MAIN_ADMIN_ID = 813096225  # Твой chat_id (только ты можешь добавлять админов)
ALLOWED_USER_IDS = [813096225]  # Список админов
SUITS = ["♥️", "♠️", "♣️", "♦️"]
SLOTS_SYMBOLS = ["🍒", "🍋", "💎", "⭐", "7️⃣"]

# Хранилища данных
user_states = {}      # Состояние: waiting_for_captcha, waiting_for_code, verified, waiting_for_bet, playing, playing_slots
user_games = {}       # Данные текущей игры (блэкджек или слоты)
user_wins = {}        # Счётчик побед (блэкджек)
user_captcha = {}     # Хранит эмодзи для капчи
user_stats = {}       # Статистика: игры, победы, макс. выигрыш, время бонуса
user_balances = {}    # Баланс халол-коинов (∞ для админов)

# Функция для форматирования карт с мастями (блэкджек)
def format_card(value):
    suit = random.choice(SUITS)
    if value == 11:
        return f"A{suit}"
    elif value == 10:
        return f"{random.choice(['J', 'Q', 'K'])}{suit}"
    else:
        return f"{value}{suit}"

# Функция для форматирования списка карт
def format_hand(hand):
    return ", ".join(format_card(value) for value in hand)

# Функция для расчёта очков в блэкджеке
def calculate_score(hand):
    score = sum(hand)
    if 11 in hand and score > 21:
        hand[hand.index(11)] = 1
        score = sum(hand)
    return score

# Функция для создания кнопок ставок
def create_bet_buttons():
    keyboard = [
        [KeyboardButton("10"), KeyboardButton("50")],
        [KeyboardButton("100"), KeyboardButton("500")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания кнопок во время блэкджека
def create_buttons():
    keyboard = [
        [KeyboardButton("Hit"), KeyboardButton("Stand"), KeyboardButton("I pass")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания кнопок во время слотов
def create_slots_buttons():
    keyboard = [
        [KeyboardButton("Spin"), KeyboardButton("Stop")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания кнопок по завершении игры
def create_end_game_buttons():
    keyboard = [
        [KeyboardButton("Restart"), KeyboardButton("I pass")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Функция для создания кнопок капчи
def create_captcha_buttons():
    keyboard = [[KeyboardButton(emoji) for emoji in EMOJI_LIST]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# Проверка баланса (∞ для админов)
def get_balance(chat_id):
    if chat_id in ALLOWED_USER_IDS:
        return "∞"
    return user_balances.get(chat_id, 10000)

# Команда /bonus
async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return
    if chat_id in ALLOWED_USER_IDS:
        await update.message.reply_text("💰 ∞ coin — bonus kerak emas!")
        return
    current_time = time.time()
    last_bonus = user_stats.get(chat_id, {}).get("last_bonus", 0)
    if current_time - last_bonus < 24 * 3600:  # 24 часа
        remaining = int(24 * 3600 - (current_time - last_bonus))
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        await update.message.reply_text(
            f"⏳ Bonus faqat {hours} soat {minutes} daqiqadan keyin olinadi!"
        )
        return
    user_balances[chat_id] = user_balances.get(chat_id, 10000) + 1000
    user_stats[chat_id]["last_bonus"] = current_time
    balance = user_balances[chat_id]
    await update.message.reply_text(
        f"🎁 +1000 halol-coin bonus!\n"
        f"💰 Balans: {balance} coin"
    )

# Команда /balance
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return
    balance = get_balance(chat_id)
    await update.message.reply_text(f"💰 Sening halol-coinlaring: {balance}")

# Команда /top
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return
    if not user_stats:
        await update.message.reply_text("📊 Hozircha hech kim o'ynamadi!")
        return
    sorted_users = sorted(
        user_stats.items(),
        key=lambda x: user_balances.get(x[0], 10000) if x[0] not in ALLOWED_USER_IDS else float('inf'),
        reverse=True
    )[:5]
    message = "🏆 Top-5 o'yinchilar:\n"
    for i, (uid, _) in enumerate(sorted_users, 1):
        try:
            chat_info = await update.message.bot.get_chat(uid)
            username = chat_info.first_name or f"User {uid}"
        except:
            username = f"User {uid}"
        balance = get_balance(uid)
        message += f"{i}. {username} — {balance} halol-coin\n"
    await update.message.reply_text(message)

# Команда /player_list
async def player_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return
    if not user_stats:
        await update.message.reply_text("📊 Hozircha hech kim o'ynamadi!")
        return
    # Сортировка: админы сверху, юзеры по балансу
    sorted_users = sorted(
        user_stats.items(),
        key=lambda x: (
            x[0] in ALLOWED_USER_IDS and float('inf'),  # Админы первые
            user_balances.get(x[0], 10000) if x[0] not in ALLOWED_USER_IDS else 0  # Юзеры по балансу
        ),
        reverse=True
    )
    message = "📋 Ro'yxat o'yinchilar:\n"
    for uid, stats in sorted_users:
        games = stats.get("games", 0)
        wins = stats.get("wins", 0)
        slots_games = stats.get("slots_games", 0)
        slots_wins = stats.get("slots_wins", 0)
        win_rate = (wins / games * 100) if games > 0 else 0
        slots_win_rate = (slots_wins / slots_games * 100) if slots_games > 0 else 0
        balance = get_balance(uid)
        rank = "Admin" if uid in ALLOWED_USER_IDS else "User"
        try:
            chat_info = await update.message.bot.get_chat(uid)
            username = chat_info.first_name or f"User {uid}"
        except:
            username = f"User {uid}"
        message += (
            f"👤 {username} ({rank})\n"
            f"💰 Balans: {balance} coin\n"
            f"🎮 Blackjack: {wins} g'alaba ({win_rate:.1f}%)\n"
            f"🎰 Slots: {slots_wins} g'alaba ({slots_win_rate:.1f}%)\n"
        )
    await update.message.reply_text(message)

# Админ-команда: показать список админов
async def admin_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Faqat adminlar uchun!")
        return
    if not ALLOWED_USER_IDS:
        await update.message.reply_text("📋 Ro'yxatda adminlar yo'q!")
        return
    message = "📋 Sписок adminlar:\n"
    for i, uid in enumerate(ALLOWED_USER_IDS, 1):
        try:
            chat_info = await update.message.bot.get_chat(uid)
            username = chat_info.first_name or f"User {uid}"
        except:
            username = f"User {uid}"
        message += f"{i}. {username} ({uid})\n"
    await update.message.reply_text(message)

# Админ-команда: добавить пользователя в ALLOWED_USER_IDS (только для MAIN_ADMIN_ID)
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id != MAIN_ADMIN_ID:
        if chat_id in ALLOWED_USER_IDS:
            await update.message.reply_text("🚫 Faqat bosh admin qo'sha oladi!")
        else:
            await update.message.reply_text("🚫 Faqat adminlar uchun!")
        return
    try:
        new_user_id = int(context.args[0])
        if new_user_id not in ALLOWED_USER_IDS:
            ALLOWED_USER_IDS.append(new_user_id)
            await update.message.reply_text(f"✅ Foydalanuvchi {new_user_id} qo'shildi!")
        else:
            await update.message.reply_text("🚫 Bu foydalanuvchi allaqachon ruxsatli!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Iltimos, to'g'ri chat_id kiriting: /add_user <chat_id>")

# Админ-команда: убрать пользователя из ALLOWED_USER_IDS
async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Faqat adminlar uchun!")
        return
    try:
        user_id = int(context.args[0])
        if user_id in ALLOWED_USER_IDS:
            ALLOWED_USER_IDS.remove(user_id)
            await update.message.reply_text(f"✅ Foydalanuvchi {user_id} o'chirildi!")
        else:
            await update.message.reply_text("🚫 Bu foydalanuvchi ruxsatli ro'yxatda yo'q!")
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Iltimos, to'g'ri chat_id kiriting: /remove_user <chat_id>")

# Админ-команда: изменить пароль
async def set_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SECRET_CODE
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Faqat adminlar uchun!")
        return
    try:
        new_code = context.args[0]
        if new_code:
            SECRET_CODE = new_code
            await update.message.reply_text(f"✅ Yangi parol o'rnatildi: {new_code}")
        else:
            await update.message.reply_text("❌ Parol bo'sh bo'lmasligi kerak!")
    except IndexError:
        await update.message.reply_text("❌ Iltimos, yangi parolni kiriting: /set_password <new_code>")

# Админ-команда: показать статистику всех игроков
async def stats_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in ALLOWED_USER_IDS:
        await update.message.reply_text("🚫 Faqat adminlar uchun!")
        return
    if not user_stats:
        await update.message.reply_text("📊 Hozircha hech kim o'ynamadi!")
        return
    message = "📊 Barcha o'yinchilar statistikasi:\n"
    for uid in user_stats:
        stats = user_stats[uid]
        games = stats.get("games", 0)
        wins = stats.get("wins", 0)
        slots_games = stats.get("slots_games", 0)
        slots_wins = stats.get("slots_wins", 0)
        max_win = stats.get("max_win", 0)
        win_rate = (wins / games * 100) if games > 0 else 0
        slots_win_rate = (slots_wins / slots_games * 100) if slots_games > 0 else 0
        balance = get_balance(uid)
        rank = "Admin" if uid in ALLOWED_USER_IDS else "User"
        try:
            chat_info = await update.message.bot.get_chat(uid)
            username = chat_info.first_name or f"User {uid}"
        except:
            username = f"User {uid}"
        message += (
            f"{username} ({rank}):\n"
            f"  💰 Balans: {balance} coin\n"
            f"  Blackjack:\n"
            f"    O'yinlar: {games}\n"
            f"    G'alabalar: {wins}\n"
            f"    G'alaba foizi: {win_rate:.1f}%\n"
            f"  Slots:\n"
            f"    O'yinlar: {slots_games}\n"
            f"    G'alabalar: {slots_wins}\n"
            f"    G'alaba foizi: {slots_win_rate:.1f}%\n"
            f"  Maksimal yutuq: {max_win} halol-coin\n"
        )
    await update.message.reply_text(message)

# Команда /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id not in user_stats:
        user_stats[chat_id] = {"games": 0, "wins": 0, "slots_games": 0, "slots_wins": 0, "max_win": 0, "last_bonus": 0}
    stats = user_stats[chat_id]
    games = stats.get("games", 0)
    wins = stats.get("wins", 0)
    slots_games = stats.get("slots_games", 0)
    slots_wins = stats.get("slots_wins", 0)
    max_win = stats.get("max_win", 0)
    win_rate = (wins / games * 100) if games > 0 else 0
    slots_win_rate = (slots_wins / slots_games * 100) if slots_games > 0 else 0
    balance = get_balance(chat_id)
    rank = "Admin" if chat_id in ALLOWED_USER_IDS else "User"
    await update.message.reply_text(
        f"📊 Sening statistikang ({rank}):\n"
        f"💰 Balans: {balance} coin\n"
        f"🎮 Blackjack:\n"
        f"  O'yinlar: {games}\n"
        f"  G'alabalar: {wins}\n"
        f"  G'alaba foizi: {win_rate:.1f}%\n"
        f"🎰 Slots:\n"
        f"  O'yinlar: {slots_games}\n"
        f"  G'alabalar: {slots_wins}\n"
        f"  G'alaba foizi: {slots_win_rate:.1f}%\n"
        f"🏆 Maksimal yutuq: {max_win} halol-coin"
    )

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    if chat_id in user_states and user_states[chat_id] == "verified":
        balance = get_balance(chat_id)
        await update.message.reply_text(
            f"SIZ PAROLNI TOG'RI KIRITBOLDINGIZ\n"
            f"💰 Balans: {balance} coin"
        )
        return

    # Пропускаем капчу и пароль для разрешённых пользователей
    if chat_id in ALLOWED_USER_IDS:
        user_states[chat_id] = "verified"
        user_wins[chat_id] = 0
        user_stats[chat_id] = {"games": 0, "wins": 0, "slots_games": 0, "slots_wins": 0, "max_win": 0, "last_bonus": 0}
        # Баланс не нужен, т.к. ∞
        await update.message.reply_text(
            "✅ TOG'RI SAN HALOLSAN ✅\n"
            "💰 Balans: ∞ coin\n"
            "🃏 Boshlash uchun /blackjack, /slots, /balance yoki /player_list",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    # Для остальных пользователей запускаем капчу
    selected_emoji = random.choice(EMOJI_LIST)
    user_captcha[chat_id] = selected_emoji
    user_states[chat_id] = "waiting_for_captcha"

    await update.message.reply_text(
        "ASSALOMU ALAYKUM!\n"
        "✅SIZ HALOL CAZINOGA HUSH KELIBSIZ✅\n"
        f"🔐 Avval captcha'dan o'ting: quyidagi emojini tanlang: {selected_emoji}",
        reply_markup=create_captcha_buttons()
    )

# Команда для слотов
async def slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return

    if chat_id not in ALLOWED_USER_IDS:
        balance = user_balances.get(chat_id, 10000)
        if balance < 10:
            user_balances[chat_id] = balance + 500
            await update.message.reply_text(
                "💰 Coinlaringiz yetmaydi! +500 coin bonus beramiz!",
                reply_markup=ReplyKeyboardRemove()
            )
            balance = user_balances[chat_id]
    else:
        balance = "∞"

    user_states[chat_id] = "waiting_for_bet"
    user_games[chat_id] = {"game_type": "slots"}
    await update.message.reply_text(
        f"💰 Balans: {balance} coin\n"
        "🎰 Qancha stavka qo'yasiz? (10, 50, 100, 500)",
        reply_markup=create_bet_buttons()
    )

# Команда для начала блэкджека
async def blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return

    if chat_id not in ALLOWED_USER_IDS:
        balance = user_balances.get(chat_id, 10000)
        if balance < 10:
            user_balances[chat_id] = balance + 500
            await update.message.reply_text(
                "💰 Coinlaringiz yetmaydi! +500 coin bonus beramiz!",
                reply_markup=ReplyKeyboardRemove()
            )
            balance = user_balances[chat_id]
    else:
        balance = "∞"

    user_states[chat_id] = "waiting_for_bet"
    user_games[chat_id] = {"game_type": "blackjack"}
    await update.message.reply_text(
        f"💰 Balans: {balance} coin\n"
        "🃏 Qancha stavka qo'yasiz? (10, 50, 100, 500)",
        reply_markup=create_bet_buttons()
    )

# Запуск блэкджека после выбора ставки
async def start_blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    # Создаём колоду
    deck = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(deck)
    player = [deck.pop(), deck.pop()]
    dealer = [deck.pop()]

    user_games[chat_id].update({
        "deck": deck,
        "player": player,
        "dealer": dealer
    })

    user_states[chat_id] = "playing"
    score = calculate_score(player)

    # Анимация раздачи
    formatted_player = format_hand([player[0]])
    await update.message.reply_text(f"🃏 Birinchi karta: {formatted_player}")
    await asyncio.sleep(1)
    formatted_player = format_hand([player[1]])
    await update.message.reply_text(f"🃏 Ikkinchi karta: {formatted_player}")
    await asyncio.sleep(1)
    formatted_dealer = format_card(dealer[0])
    await update.message.reply_text(
        f"🃏 Sizning kartalaringiz: {format_hand(player)}\n"
        f"Sizning ochko: {score}\n\n"
        f"Dilerning kartasi: {formatted_dealer} ❓❓\n"
        "Yozing: 'Hit' (yana karta), 'Stand' (to'xtash) yoki 'I pass' (sdat'sya)",
        reply_markup=create_buttons()
    )

    # Проверка на блэкджек
    await check_blackjack(update, context, chat_id)

# Запуск слотов после выбора ставки
async def start_slots(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    user_states[chat_id] = "playing_slots"
    user_stats[chat_id]["slots_games"] = user_stats.get(chat_id, {"slots_games": 0})["slots_games"] + 1
    bet = user_games[chat_id]["bet"]
    if chat_id not in ALLOWED_USER_IDS:
        user_balances[chat_id] -= bet
        balance = user_balances[chat_id]
    else:
        balance = "∞"

    # Анимация вращения барабанов
    await update.message.reply_text("🎰 Крутим барабаны...")
    result = [random.choice(SLOTS_SYMBOLS) for _ in range(3)]
    for i in range(3):
        await asyncio.sleep(0.5)
        await update.message.reply_text(f"🎰 [{result[0] if i >= 0 else '❓'}] [{result[1] if i >= 1 else '❓'}] [{result[2] if i >= 2 else '❓'}]")

    # Проверка результата
    if result[0] == result[1] == result[2]:
        message = f"🎉 Pobeda katta! {result[0]}{result[1]}{result[2]}"
        winnings = int(3 * bet)
        user_stats[chat_id]["slots_wins"] = user_stats.get(chat_id, {"slots_wins": 0})["slots_wins"] + 1
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        message = f"🥳 Yaxshi natija! {result[0]}{result[1]}{result[2]}"
        winnings = int(1.5 * bet)
        user_stats[chat_id]["slots_wins"] = user_stats.get(chat_id, {"slots_wins": 0})["slots_wins"] + 1
    else:
        message = f"😔 Omad yo'q: {result[0]}{result[1]}{result[2]}"
        winnings = 0

    if chat_id not in ALLOWED_USER_IDS:
        user_balances[chat_id] += winnings
        user_stats[chat_id]["max_win"] = max(user_stats[chat_id].get("max_win", 0), winnings)
        balance = user_balances[chat_id]
    else:
        balance = "∞"

    await update.message.reply_text(
        f"{message}\n"
        f"💰 Yutuq: {winnings} coin\n"
        f"💰 Balans: {balance} coin\n"
        f"🎰 Yana o'ynash uchun 'Spin' yoki chiqish uchun 'Stop'",
        reply_markup=create_slots_buttons()
    )

# Проверка на блэкджек
async def check_blackjack(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    game = user_games[chat_id]
    player_score = calculate_score(game['player'])

    if player_score == 21 and len(game['player']) == 2:
        if len(game['deck']) > 0:
            card = random.choice(game['deck'])
            game['deck'].remove(card)
            game['dealer'].append(card)
        else:
            await update.message.reply_text(
                "🃏 Koloda bo'sh! O'yin tugadi.",
                reply_markup=create_end_game_buttons()
            )
            user_states[chat_id] = "verified"
            user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1
            bet = game["bet"]
            if chat_id not in ALLOWED_USER_IDS:
                user_balances[chat_id] -= bet
                balance = user_balances[chat_id]
            else:
                balance = "∞"
            await update.message.reply_text(
                f"💰 Balans: {balance} coin",
                reply_markup=create_end_game_buttons()
            )
            del user_games[chat_id]
            return False

        dealer_score = calculate_score(game['dealer'])
        formatted_player = format_hand(game['player'])
        formatted_dealer = format_hand(game['dealer'])
        user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1
        bet = game["bet"]

        if dealer_score == 21 and len(game['dealer']) == 2:
            await update.message.reply_text(
                f"🃏 Sizning kartalaringiz: {formatted_player} (Blackjack!)\n"
                f"Dilerning kartasi: {formatted_dealer} (Blackjack!)\n"
                "🤝 Durrang! Coinlar qaytarildi.",
                reply_markup=create_end_game_buttons()
            )
            balance = get_balance(chat_id)
        else:
            winnings = int(3 * bet)
            if chat_id not in ALLOWED_USER_IDS:
                user_balances[chat_id] += winnings
                user_stats[chat_id]["max_win"] = max(user_stats[chat_id].get("max_win", 0), winnings)
                balance = user_balances[chat_id]
            else:
                balance = "∞"
            await update.message.reply_text(
                f"🃏 Sizning kartalaringiz: {formatted_player} (Blackjack!)\n"
                f"Dilerning kartasi: {formatted_dealer}\n"
                f"✅ Siz yutdingiz! +{winnings} coin",
                reply_markup=create_end_game_buttons()
            )
            user_wins[chat_id] = user_wins.get(chat_id, 0) + 1
            user_stats[chat_id]["wins"] = user_stats.get(chat_id, {"wins": 0})["wins"] + 1

        await update.message.reply_text(
            f"🏆 Sening g'alabalaringiz: {user_wins.get(chat_id, 0)}\n"
            f"💰 Balans: {balance} coin",
            reply_markup=create_end_game_buttons()
        )
        user_states[chat_id] = "verified"
        del user_games[chat_id]
        return True
    return False

# Перезапуск игры (блэкджек)
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id

    if user_states.get(chat_id) != "verified":
        await update.message.reply_text("🚫 Avval to'g'ri kodni kiriting!", reply_markup=ReplyKeyboardRemove())
        return

    if chat_id not in ALLOWED_USER_IDS:
        balance = user_balances.get(chat_id, 10000)
        if balance < 10:
            user_balances[chat_id] = balance + 500
            await update.message.reply_text(
                "💰 Coinlaringiz yetmaydi! +500 coin bonus beramiz!",
                reply_markup=ReplyKeyboardRemove()
            )
            balance = user_balances[chat_id]
    else:
        balance = "∞"

    user_states[chat_id] = "waiting_for_bet"
    user_games[chat_id] = {"game_type": "blackjack"}
    await update.message.reply_text(
        f"💰 Balans: {balance} coin\n"
        "🃏 Qancha stavka qo'yasiz? (10, 50, 100, 500)",
        reply_markup=create_bet_buttons()
    )

# Обработка текстовых сообщений, капчи, ставок и игровых действий
async def check_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat.id
    text = update.message.text.strip()

    # Обработка капчи
    if user_states.get(chat_id) == "waiting_for_captcha":
        expected_emoji = user_captcha.get(chat_id)
        if text == expected_emoji:
            user_states[chat_id] = "waiting_for_code"
            if chat_id in user_captcha:
                del user_captcha[chat_id]
            await update.message.reply_text(
                "‼️BOSHLASH UCHUN KODNI KIRITING‼️",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text(
                f"Noto'g'ri emoji! Iltimos, quyidagi emojini tanlang: {expected_emoji}",
                reply_markup=create_captcha_buttons()
            )
        return

    # Проверка кода доступа
    if user_states.get(chat_id) == "waiting_for_code":
        if text == SECRET_CODE:
            user_states[chat_id] = "verified"
            user_wins[chat_id] = 0
            user_stats[chat_id] = {"games": 0, "wins": 0, "slots_games": 0, "slots_wins": 0, "max_win": 0, "last_bonus": 0}
            user_balances[chat_id] = user_balances.get(chat_id, 10000)  # Начальный баланс 10,000
            await update.message.reply_text(
                "✅ TOG'RI SAN HALOLSAN ✅\n"
                f"💰 Balans: {user_balances[chat_id]} coin\n"
                "🃏 Boshlash uchun /blackjack, /slots, /balance yoki /player_list\n"
                "🎁 Har kuni /bonus bilan +1000 coin!",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("HAROMA CHIQ NAXUY")
        return

    # Обработка выбора ставки
    if user_states.get(chat_id) == "waiting_for_bet":
        try:
            bet = int(text)
            if bet not in [10, 50, 100, 500]:
                await update.message.reply_text(
                    "❌ Iltimos, faqat 10, 50, 100 yoki 500 coin tanlang!",
                    reply_markup=create_bet_buttons()
                )
                return
            if chat_id not in ALLOWED_USER_IDS:
                balance = user_balances.get(chat_id, 10000)
                if balance < bet:
                    user_balances[chat_id] = balance + 500
                    await update.message.reply_text(
                        "💰 Coinlaringiz yetmaydi! +500 coin bonus beramiz!",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    user_states[chat_id] = "verified"
                    return
            user_games[chat_id]["bet"] = bet
            if user_games[chat_id]["game_type"] == "blackjack":
                await start_blackjack(update, context, chat_id)
            elif user_games[chat_id]["game_type"] == "slots":
                await start_slots(update, context, chat_id)
        except ValueError:
            await update.message.reply_text(
                "❌ Iltimos, faqat 10, 50, 100 yoki 500 coin tanlang!",
                reply_markup=create_bet_buttons()
            )
        return

    # Обработка действий в слотах
    if user_states.get(chat_id) == "playing_slots":
        text = text.lower()
        if text == "spin":
            if chat_id not in ALLOWED_USER_IDS:
                balance = user_balances.get(chat_id, 10000)
                if balance < 10:
                    user_balances[chat_id] = balance + 500
                    await update.message.reply_text(
                        "💰 Coinlaringiz yetmaydi! +500 coin bonus beramiz!",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    user_states[chat_id] = "verified"
                    return
            else:
                balance = "∞"

            user_states[chat_id] = "waiting_for_bet"
            user_games[chat_id] = {"game_type": "slots"}
            await update.message.reply_text(
                f"💰 Balans: {balance} coin\n"
                "🎰 Qancha stavka qo'yasiz? (10, 50, 100, 500)",
                reply_markup=create_bet_buttons()
            )
            return
        elif text == "stop":
            user_states[chat_id] = "verified"
            balance = get_balance(chat_id)
            await update.message.reply_text(
                f"🎰 Slotidan chiqdingiz!\n"
                f"💰 Balans: {balance} coin\n"
                "/blackjack, /slots, /balance yoki /player_list",
                reply_markup=create_end_game_buttons()
            )
            if chat_id in user_games:
                del user_games[chat_id]
            return
        else:
            await update.message.reply_text(
                "Iltimos, faqat 'Spin' yoki 'Stop' ni tanlang.",
                reply_markup=create_slots_buttons()
            )
            return

    # Обработка действий в блэкджеке
    if user_states.get(chat_id) == "playing":
        if chat_id not in user_games:
            await update.message.reply_text(
                "🧐 O'yin topilmadi. /blackjack yozib qayta boshlang.",
                reply_markup=ReplyKeyboardRemove()
            )
            user_states[chat_id] = "verified"
            return

        game = user_games[chat_id]
        text = text.lower()
        bet = game["bet"]

        if text == "hit":
            if not game['deck']:
                await update.message.reply_text(
                    "🃏 Koloda bo'sh! O'yin tugadi.",
                    reply_markup=create_end_game_buttons()
                )
                user_states[chat_id] = "verified"
                user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1
                if chat_id not in ALLOWED_USER_IDS:
                    user_balances[chat_id] -= bet
                    balance = user_balances[chat_id]
                else:
                    balance = "∞"
                await update.message.reply_text(
                    f"💰 Balans: {balance} coin",
                    reply_markup=create_end_game_buttons()
                )
                del user_games[chat_id]
                return

            await update.message.reply_text("🃏 Razdaём kartu...")
            await asyncio.sleep(1)
            card = random.choice(game['deck'])
            game['deck'].remove(card)
            game['player'].append(card)

            score = calculate_score(game['player'])
            formatted_card = format_card(card)
            await update.message.reply_text(
                f"🃏 Yangi karta: {formatted_card}\n"
                f"Sizning ochko: {score}"
            )

            if score > 21:
                await update.message.reply_text(
                    f"❌ Siz yutqazdingiz! 21 dan oshdi. -{bet} coin",
                    reply_markup=create_end_game_buttons()
                )
                user_states[chat_id] = "verified"
                user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1
                if chat_id not in ALLOWED_USER_IDS:
                    user_balances[chat_id] -= bet
                    balance = user_balances[chat_id]
                else:
                    balance = "∞"
                await update.message.reply_text(
                    f"💰 Balans: {balance} coin",
                    reply_markup=create_end_game_buttons()
                )
                del user_games[chat_id]
            return

        elif text == "stand":
            player_score = calculate_score(game['player'])
            dealer_score = calculate_score(game['dealer'])

            while dealer_score < 17 and game['deck']:
                card = random.choice(game['deck'])
                game['deck'].remove(card)
                game['dealer'].append(card)
                dealer_score = calculate_score(game['dealer'])

            formatted_player = format_hand(game['player'])
            formatted_dealer = format_hand(game['dealer'])
            user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1

            if dealer_score > 21:
                winnings = int(2 * bet)
                result = f"✅ Siz yutdingiz! Diler 21 dan oshdi! +{winnings} coin"
                user_wins[chat_id] = user_wins.get(chat_id, 0) + 1
                user_stats[chat_id]["wins"] = user_stats.get(chat_id, {"wins": 0})["wins"] + 1
                if chat_id not in ALLOWED_USER_IDS:
                    user_balances[chat_id] += winnings
                    user_stats[chat_id]["max_win"] = max(user_stats[chat_id].get("max_win", 0), winnings)
                    balance = user_balances[chat_id]
                else:
                    balance = "∞"
            else:
                result = (
                    f"Sizning kartalaringiz: {formatted_player} ({player_score})\n"
                    f"Dilerning kartalaringiz: {formatted_dealer} ({dealer_score})\n"
                )
                if dealer_score > player_score:
                    result += f"❌ Siz yutqazdingiz! -{bet} coin"
                    if chat_id not in ALLOWED_USER_IDS:
                        user_balances[chat_id] -= bet
                    balance = get_balance(chat_id)
                elif player_score == dealer_score:
                    result += "🤝 Durrang! Coinlar qaytarildi."
                    balance = get_balance(chat_id)
                else:
                    winnings = int(2 * bet)
                    result += f"✅ Siz yutdingiz! +{winnings} coin"
                    user_wins[chat_id] = user_wins.get(chat_id, 0) + 1
                    user_stats[chat_id]["wins"] = user_stats.get(chat_id, {"wins": 0})["wins"] + 1
                    if chat_id not in ALLOWED_USER_IDS:
                        user_balances[chat_id] += winnings
                        user_stats[chat_id]["max_win"] = max(user_stats[chat_id].get("max_win", 0), winnings)
                        balance = user_balances[chat_id]
                    else:
                        balance = "∞"

            await update.message.reply_text(result)
            await update.message.reply_text(
                f"🏆 Sening g'alabalaringiz: {user_wins.get(chat_id, 0)}\n"
                f"💰 Balans: {balance} coin",
                reply_markup=create_end_game_buttons()
            )
            user_states[chat_id] = "verified"
            del user_games[chat_id]
            return

        elif text == "i pass":
            await update.message.reply_text(
                f"Siz o'zingizni topshirdingiz. Diler g'olib! -{bet} coin",
                reply_markup=create_end_game_buttons()
            )
            user_states[chat_id] = "verified"
            user_stats[chat_id]["games"] = user_stats.get(chat_id, {"games": 0, "wins": 0})["games"] + 1
            if chat_id not in ALLOWED_USER_IDS:
                user_balances[chat_id] -= bet
                balance = user_balances[chat_id]
            else:
                balance = "∞"
            await update.message.reply_text(
                f"💰 Balans: {balance} coin",
                reply_markup=create_end_game_buttons()
            )
            del user_games[chat_id]
            return

        # Если введена некорректная команда во время игры
        await update.message.reply_text(
            "Iltimos, faqat 'Hit', 'Stand' yoki 'I pass' ni tanlang.",
            reply_markup=create_buttons()
        )
        return

    # Обработка кнопки Restart вне игры
    elif text.lower() == "restart" and user_states.get(chat_id) == "verified":
        await restart(update, context)
        return

    # Обработка I pass вне игры
    elif text.lower() == "i pass" and user_states.get(chat_id) == "verified":
        balance = get_balance(chat_id)
        await update.message.reply_text(
            f"🎮 O'yin tanlang: /blackjack, /slots, /balance yoki /player_list\n"
            f"💰 Balans: {balance} coin",
            reply_markup=create_end_game_buttons()
        )
        return

# Запуск бота
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("blackjack", blackjack))
    app.add_handler(CommandHandler("slots", slots))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("bonus", bonus))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("player_list", player_list))
    app.add_handler(CommandHandler("admin_list", admin_list))
    app.add_handler(CommandHandler("add_user", add_user))
    app.add_handler(CommandHandler("remove_user", remove_user))
    app.add_handler(CommandHandler("set_password", set_password))
    app.add_handler(CommandHandler("stats_all", stats_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_code))

    print("Халол Казино включено 🎰")
    app.run_polling()
