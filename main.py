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
registered_users = set() 
temp_data = {}
last_full_list = []

# --- স্লট লিস্ট তৈরি ফাংশন ---
def get_slot_list_text(target_list, is_full=False):
    text = "🏆 **Tournament Slot Status** 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    if is_full:
        for i, team in enumerate(target_list, 1):
            text += f"{i}. 🎮 {team['team_name']}\n   👤 {team['user_display_name']} (@{team['username']})\n"
    else:
        for i in range(1, 13):
            if i <= len(target_list):
                team = target_list[i-1]
                text += f"✅ Slot {i}: {team['team_name']} (@{team['username']})\n"
            else:
                text += f"⬜ Slot {i}: খালি\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    return text

# --- সিকিউরিটি চেক (অ্যাডমিন ইনবক্স) ---
def is_admin_private(message):
    return message.chat.type == 'private' and message.from_user.id == ADMIN_ID

# --- ১. উইনার সিস্টেম (Case-Insensitive) ---
@bot.message_handler(commands=['winner', 'Winner'], func=is_admin_private)
def select_winner(message):
    target = confirmed_teams if confirmed_teams else last_full_list
    if not target:
        bot.send_message(ADMIN_ID, "❌ বর্তমানে কোনো রেজিস্ট্রেশন করা টিম নেই।")
        return
    
    markup = types.InlineKeyboardMarkup()
    for i, team in enumerate(target):
        markup.add(types.InlineKeyboardButton(f"স্লট {i+1}: {team['team_name']}", callback_data=f"win_{i}"))
    
    bot.send_message(ADMIN_ID, "🏆 উইনার টিমের ওপর ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('win_') and call.from_user.id == ADMIN_ID)
def declare_winner(call):
    index = int(call.data.split('_')[1])
    target = confirmed_teams if confirmed_teams else last_full_list
    
    if index < len(target):
        winner_team = target[index]
        winner_msg = (
            f"🎊 **অভিনন্দন {winner_team['user_display_name']}!!** 🎊\n\n"
            f"আপনার টিম **{winner_team['team_name']}** টুর্নামেন্টে **বিজয়ী (WINNER)** হয়েছে! 🏆🔥\n\n"
            "অ্যাডমিন শীঘ্রই পুরস্কারের জন্য যোগাযোগ করবে।"
        )
        try:
            bot.send_message(winner_team['user_id'], winner_msg, parse_mode="Markdown")
            bot.edit_message_text(f"✅ {winner_team['team_name']} কে উইনার ঘোষণা করা হয়েছে!", call.message.chat.id, call.message.message_id)
        except:
            bot.send_message(ADMIN_ID, "❌ ইউজারের ইনবক্স বন্ধ, মেসেজ যায়নি।")

# --- ২. অ্যাডমিন কমান্ডস ---
@bot.message_handler(commands=['allclear', 'on', 'off', 'mode', 'sendlink'], func=is_admin_private)
def admin_ops(message):
    global reg_status, reg_mode, confirmed_teams, registered_users, temp_data, last_full_list
    cmd = message.text.split()[0].lower()
    
    if cmd == '/allclear':
        confirmed_teams, registered_users, temp_data, last_full_list = [], set(), {}, []
        bot.send_message(ADMIN_ID, "♻️ সব ডাটা মুছে ফেলা হয়েছে।")
    elif cmd == '/on':
        reg_status = True
        bot.send_message(ADMIN_ID, "✅ রেজিস্ট্রেশন চালু করা হয়েছে।")
    elif cmd == '/off':
        reg_status = False
        bot.send_message(ADMIN_ID, "🛑 রেজিস্ট্রেশন বন্ধ করা হয়েছে।")
    elif cmd == '/mode':
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Free Mode 🆓", callback_data="set_free"),
                   types.InlineKeyboardButton("Paid Mode 💰", callback_data="set_paid"))
        bot.send_message(ADMIN_ID, "টুর্নামেন্ট মোড পরিবর্তন করুন:", reply_markup=markup)
    elif cmd == '/sendlink':
        if not last_full_list:
            bot.send_message(ADMIN_ID, "❌ পাঠানোর মতো কোনো লিস্ট নেই।")
            return
        for t in last_full_list:
            try: bot.send_message(t['user_id'], f"অভিনন্দন! টুর্নামেন্ট গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ লিঙ্ক পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_') and call.from_user.id == ADMIN_ID)
def handle_mode_set(call):
    global reg_mode
    reg_mode = call.data.split('_')[1]
    bot.edit_message_text(f"✅ মোড পরিবর্তন হয়েছে: {reg_mode.upper()}", call.message.chat.id, call.message.message_id)

# --- ৩. গ্রুপ রেজিস্ট্রেশন ---
@bot.message_handler(commands=['reg'], func=lambda m: m.chat.type != 'private')
def start_reg(message):
    if not reg_status:
        bot.reply_to(message, "🛑 দুঃখিত, এখন রেজিস্ট্রেশন বন্ধ আছে।")
        return
    if message.from_user.id in registered_users:
        bot.reply_to(message, "❌ আপনি ইতিমধ্যে এই স্লটে আছেন।")
        return
    if len(confirmed_teams) >= 12:
        bot.reply_to(message, "🚫 ১২টি স্লট পূর্ণ হয়ে গেছে।")
        return

    msg = bot.send_message(message.chat.id, f"🎮 **টিম {len(confirmed_teams)+1}/12** এর জন্য নাম লিখুন:")
    bot.register_next_step_handler(msg, get_team_name)

def get_team_name(message):
    if message.chat.type == 'private' or not message.text: return
    team_name = message.text
    user_id = message.from_user.id
    
    temp_data[user_id] = {
        'team_name': team_name,
        'user_display_name': message.from_user.first_name,
        'username': message.from_user.username if message.from_user.username else "NoUser"
    }
    
    if reg_mode == "paid":
        payment_text = (
            "✨ **পেমেন্ট তথ্য** ✨\n"
            "━━━━━━━━━━━━━━\n"
            f"বিকাশ/নগদ/রকেট (Personal):\n`{PAYMENT_NUMBER}`\n\n"
            "টাকা পাঠিয়ে স্ক্রিনশট বা ট্রানজেকশন আইডি দিন।"
        )
        bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(user_id)
        bot.send_message(message.chat.id, f"✅ আপনার স্লট বুক হয়েছে!\n\n{get_slot_list_text(confirmed_teams)}", parse_mode="Markdown")

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data.get(user_id)
    if not team_info: return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট চেক:\nটিম: {team_info['team_name']}\nনাম: {team_info['user_display_name']}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ তথ্য পাঠানো হয়েছে। অ্যাডমিন চেক করছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')) and call.from_user.id == ADMIN_ID)
def admin_decision(call):
    action, uid = call.data.split('_')
    uid = int(uid)
    if action == 'app':
        complete_registration(uid)
        bot.send_message(uid, f"✅ আপনার স্লট কনফার্ম হয়েছে!\n\n{get_slot_list_text(confirmed_teams)}", parse_mode="Markdown")
        if call.message.photo:
            bot.edit_message_caption("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.edit_message_text("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ পেমেন্ট বাতিল হয়েছে।")

def complete_registration(uid):
    global confirmed_teams, last_full_list, registered_users
    if uid not in temp_data: return
    data = temp_data[uid]
    data['user_id'] = uid
    confirmed_teams.append(data)
    registered_users.add(uid)
    
    if len(confirmed_teams) == 12:
        bot.send_message(ADMIN_ID, f"🔥 ১২ জন পূর্ণ হয়েছে!\n\n{get_slot_list_text(confirmed_teams, True)}\nলিঙ্ক পাঠাতে /sendlink দিন।")
        last_full_list = list(confirmed_teams)
        confirmed_teams = [] 

# ৪. পাবলিক লিস্ট ও স্টার্ট
@bot.message_handler(commands=['list'])
def show_list(message):
    bot.send_message(message.chat.id, get_slot_list_text(confirmed_teams if confirmed_teams else last_full_list), parse_mode="Markdown")

@bot.message_handler(commands=['start'])
def welcome(message):
    if message.chat.type == 'private' and message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, f"রেজিস্ট্রেশন করতে গ্রুপে জয়েন করুন:\n{TOURNAMENT_GROUP_LINK}\n\nসেখানে /reg লিখুন।")
    else:
        bot.reply_to(message, "স্বাগতম! টুর্নামেন্ট ম্যানেজমেন্ট বট চালু আছে।")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
