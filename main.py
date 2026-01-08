import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- Koyeb Health Check Server (Port 8000) ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- কনফিগারেশন ---
API_TOKEN = '7960268103:AAGkoU1DF7igV2ZxQa_2V51VHTUlJv2Q96o'
TOURNAMENT_GROUP_LINK = "https://t.me/sgsgfsga"
ADMIN_ID = 7707686630 
PAYMENT_NUMBER = "01704400069"

bot = telebot.TeleBot(API_TOKEN)

# ডাটাবেজ
reg_status = True  
reg_mode = "free"  
confirmed_teams = [] 
all_groups_data = [] 
registered_users = set() 
temp_data = {}

# --- স্লট এবং গ্রুপ নাম বের করা ---
def get_group_name():
    group_index = len(all_groups_data)
    return chr(65 + group_index) # A, B, C...

def get_slot_list_text(target_list, current_group):
    text = f"🏆 **Tournament Slot Status (Group {current_group})** 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 13):
        if i <= len(target_list):
            team = target_list[i-1]
            text += f"✅ Slot {i}: {team['team_name']} (@{team['username']})\n"
        else:
            text += f"⬜ Slot {i}: খালি\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    return text

# --- সিকিউরিটি চেক ---
def is_admin_private(message):
    return message.chat.type == 'private' and message.from_user.id == ADMIN_ID

# --- ১. নতুন টুর্নামেন্ট শুরু (ফিনিশ) ---
@bot.message_handler(commands=['finish'], func=is_admin_private)
def finish_tournament(message):
    global confirmed_teams, all_groups_data, registered_users, temp_data
    confirmed_teams, all_groups_data, registered_users, temp_data = [], [], set(), {}
    bot.send_message(ADMIN_ID, "🎊 **পুরো টুর্নামেন্ট ডাটা ক্লিয়ার করা হয়েছে!**\nএখন সবাই নতুন করে শুরু করতে পারবে।")

# --- ২. উইনার সিস্টেম ---
@bot.message_handler(commands=['winner', 'Winner'], func=is_admin_private)
def select_winner(message):
    target = confirmed_teams + [item for sublist in all_groups_data for item in sublist]
    if not target:
        bot.send_message(ADMIN_ID, "❌ কোনো রেজিস্ট্রেশন পাওয়া যায়নি।")
        return
    markup = types.InlineKeyboardMarkup()
    for i, team in enumerate(target):
        markup.add(types.InlineKeyboardButton(f"{team['team_name']} (@{team['username']})", callback_data=f"win_{i}"))
    bot.send_message(ADMIN_ID, "🏆 উইনার ঘোষণা করতে টিমে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('win_') and call.from_user.id == ADMIN_ID)
def declare_winner(call):
    index = int(call.data.split('_')[1])
    target = confirmed_teams + [item for sublist in all_groups_data for item in sublist]
    if index < len(target):
        winner_team = target[index]
        winner_msg = f"🎊 **অভিনন্দন {winner_team['user_display_name']}!!** 🎊\n\nআপনার টিম **{winner_team['team_name']}** টুর্নামেন্টে **বিজয়ী (WINNER)** হয়েছে! 🏆🔥"
        try: bot.send_message(winner_team['user_id'], winner_msg, parse_mode="Markdown")
        except: pass
        bot.edit_message_text(f"✅ {winner_team['team_name']} কে উইনার ঘোষণা করা হয়েছে!", call.message.chat.id, call.message.message_id)

# --- ৩. অ্যাডমিন কন্ট্রোল ---
@bot.message_handler(commands=['on', 'off', 'mode'], func=is_admin_private)
def admin_ops(message):
    global reg_status, reg_mode
    cmd = message.text.split()[0].lower()
    if cmd == '/on':
        reg_status = True
        bot.send_message(ADMIN_ID, "✅ রেজিস্ট্রেশন এখন চালু।")
    elif cmd == '/off':
        reg_status = False
        bot.send_message(ADMIN_ID, "🛑 রেজিস্ট্রেশন এখন বন্ধ।")
    elif cmd == '/mode':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Free Mode 🆓", callback_data="set_free"),
                   types.InlineKeyboardButton("Paid Mode 💰", callback_data="set_paid"))
        bot.send_message(ADMIN_ID, "মোড পরিবর্তন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_') and call.from_user.id == ADMIN_ID)
def handle_mode_set(call):
    global reg_mode
    reg_mode = call.data.split('_')[1]
    bot.edit_message_text(f"✅ মোড: {reg_mode.upper()}", call.message.chat.id, call.message.message_id)

# --- ৪. আধুনিক রেজিস্ট্রেশন সিস্টেম (/reg TeamName) ---
@bot.message_handler(commands=['reg'], func=lambda m: m.chat.type != 'private')
def register_one_line(message):
    global reg_status, confirmed_teams, registered_users
    
    # শুধু /reg লিখলে নির্দেশনা দিবে
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ **ভুল নিয়ম!**\n\nরেজিস্ট্রেশন করতে আপনার টিমের নামসহ এভাবে লিখুন:\n`/reg [টিমের নাম]`\n\nউদাহরণ: `/reg Team Tigers` ", parse_mode="Markdown")
        return

    if not reg_status:
        bot.reply_to(message, "🛑 রেজিস্ট্রেশন এখন বন্ধ আছে।")
        return
    if message.from_user.id in registered_users:
        bot.reply_to(message, "❌ আপনি ইতিমধ্যে এই টুর্নামেন্টে নাম লিখিয়েছেন।")
        return
    if len(confirmed_teams) >= 12:
        bot.reply_to(message, "🚫 ১২টি স্লট পূর্ণ হয়ে গেছে। পরবর্তী গ্রুপের জন্য অপেক্ষা করুন।")
        return

    team_name = args[1]
    user_id = message.from_user.id
    
    # সাময়িক ডাটা সেভ
    temp_data[user_id] = {
        'team_name': team_name,
        'user_display_name': message.from_user.first_name,
        'username': message.from_user.username if message.from_user.username else "NoUser",
        'user_id': user_id
    }

    if reg_mode == "paid":
        bot.send_message(message.chat.id, f"💰 **পেইড টুর্নামেন্ট**\nনম্বর: `{PAYMENT_NUMBER}`\nটাকা পাঠিয়ে স্ক্রিনশট দিন।", parse_mode="Markdown")
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(user_id, message.chat.id)

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data.get(user_id)
    if not team_info: return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}_{message.chat.id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}_{message.chat.id}"))
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট চেক: {team_info['team_name']}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ তথ্য পাঠানো হয়েছে। অ্যাডমিন চেক করছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')) and call.from_user.id == ADMIN_ID)
def admin_decision(call):
    _, uid, chat_id = call.data.split('_')
    uid, chat_id = int(uid), int(chat_id)
    if _.startswith('app'):
        complete_registration(uid, chat_id)
        bot.send_message(uid, "✅ আপনার স্লট কনফার্ম হয়েছে!")
    else:
        bot.send_message(uid, "❌ পেমেন্ট বাতিল হয়েছে।")

def complete_registration(uid, chat_id):
    global confirmed_teams, all_groups_data, registered_users
    data = temp_data[uid]
    confirmed_teams.append(data)
    registered_users.add(uid)
    
    current_grp = get_group_name()
    bot.send_message(chat_id, f"✅ স্লট বুক হয়েছে!\n\n{get_slot_list_text(confirmed_teams, current_grp)}", parse_mode="Markdown")

    if len(confirmed_teams) == 12:
        bot.send_message(ADMIN_ID, f"🔥 Group {current_grp} পূর্ণ হয়েছে! লিঙ্ক পাঠাতে /sendlink লিখুন।")
        all_groups_data.append(list(confirmed_teams))
        confirmed_teams = [] 

# --- ৫. অন্যান্য কমান্ড ---
@bot.message_handler(commands=['sendlink'], func=is_admin_private)
def send_link(message):
    if not all_groups_data:
        bot.send_message(ADMIN_ID, "❌ কোনো পূর্ণ গ্রুপ নেই।")
        return
    for t in all_groups_data[-1]:
        try: bot.send_message(t['user_id'], f"গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}")
        except: pass
    bot.send_message(ADMIN_ID, "✅ সর্বশেষ গ্রুপকে লিঙ্ক পাঠানো হয়েছে।")

@bot.message_handler(commands=['list'])
def show_list(message):
    bot.send_message(message.chat.id, get_slot_list_text(confirmed_teams, get_group_name()), parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def start_msg(message):
    if message.chat.type == 'private' and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, f"রেজিস্ট্রেশন করতে গ্রুপে জয়েন করুন:\n{TOURNAMENT_GROUP_LINK}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
