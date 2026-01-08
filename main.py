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
registered_users = set() # আইডি চেক করার জন্য
temp_data = {}
last_full_list = []

# --- স্লট লিস্ট তৈরি ফাংশন ---
def get_slot_list_text(target_list):
    if not target_list:
        return "স্লট এখনো খালি আছে।"
    text = "🏆 **Tournament Slot List** 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i, team in enumerate(target_list, 1):
        text += f"{i}. {team['team_name']} (@{team['username']})\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    return text

# --- ১. উইনার সিস্টেম (শুধুমাত্র অ্যাডমিন ইনবক্স) ---
@bot.message_handler(commands=['winner'], func=lambda m: m.chat.type == 'private' and m.from_user.id == ADMIN_ID)
def select_winner(message):
    if not last_full_list:
        bot.send_message(ADMIN_ID, "❌ আগে ১২ জনের রেজিস্ট্রেশন পূর্ণ হতে দিন।")
        return
    
    markup = types.InlineKeyboardMarkup()
    for i, team in enumerate(last_full_list):
        markup.add(types.InlineKeyboardButton(f"Slot {i+1}: {team['team_name']}", callback_data=f"win_{i}"))
    
    bot.send_message(ADMIN_ID, "🏆 নিচের লিস্ট থেকে উইনার টিমের ওপর ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('win_') and call.from_user.id == ADMIN_ID)
def declare_winner(call):
    index = int(call.data.split('_')[1])
    winner_team = last_full_list[index]
    
    winner_msg = (
        f"🎊 **অভিনন্দন!!** 🎊\n\n"
        f"আপনার টিম **{winner_team['team_name']}** টুর্নামেন্টে **বিজয়ী (WINNER)** নির্বাচিত হয়েছে! 🏆🔥\n\n"
        "অ্যাডমিন শীঘ্রই আপনার সাথে পুরস্কারের জন্য যোগাযোগ করবে।"
    )
    
    try:
        bot.send_message(winner_team['user_id'], winner_msg, parse_mode="Markdown")
        bot.edit_message_text(f"✅ {winner_team['team_name']} কে উইনার ঘোষণা করা হয়েছে!", call.message.chat.id, call.message.message_id)
    except:
        bot.send_message(ADMIN_ID, f"❌ {winner_team['team_name']} এর ইনবক্স ব্লক করা।")

# --- ২. অ্যাডমিন কমান্ডস (In Inbox) ---
@bot.message_handler(commands=['allclear', 'on', 'off', 'mode', 'sendlink'], func=lambda m: m.chat.type == 'private' and m.from_user.id == ADMIN_ID)
def admin_ops(message):
    global reg_status, reg_mode, confirmed_teams, registered_users, temp_data, last_full_list
    cmd = message.text.split()[0]
    
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
        bot.send_message(ADMIN_ID, "মোড পরিবর্তন করুন:", reply_markup=markup)
    elif cmd == '/sendlink':
        if not last_full_list:
            bot.send_message(ADMIN_ID, "❌ কোনো লিস্ট পাওয়া যায়নি।")
            return
        for t in last_full_list:
            try: bot.send_message(t['user_id'], f"টুর্নামেন্ট গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ ১২ জনকে লিঙ্ক পাঠানো হয়েছে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_') and call.from_user.id == ADMIN_ID)
def handle_mode_set(call):
    global reg_mode
    reg_mode = call.data.split('_')[1]
    bot.edit_message_text(f"✅ মোড: {reg_mode.upper()}", call.message.chat.id, call.message.message_id)

# --- ৩. গ্রুপ রেজিস্ট্রেশন (নম্বর ভেরিফিকেশন ছাড়া) ---
@bot.message_handler(commands=['reg'], func=lambda m: m.chat.type != 'private')
def start_reg(message):
    if not reg_status:
        bot.reply_to(message, "🛑 রেজিস্ট্রেশন বন্ধ আছে।")
        return
    if message.from_user.id in registered_users:
        bot.reply_to(message, "❌ আপনি অলরেডি রেজিস্ট্রেশন করেছেন।")
        return
    if len(confirmed_teams) >= 12:
        bot.reply_to(message, "🚫 ১২টি স্লট পূর্ণ হয়ে গেছে।")
        return

    msg = bot.send_message(message.chat.id, f"🎮 স্লট {len(confirmed_teams)+1}/12: আপনার **টিমের নাম** লিখুন:")
    bot.register_next_step_handler(msg, get_team_name)

def get_team_name(message):
    if message.chat.type == 'private' or not message.text: return
    team_name = message.text
    user_id = message.from_user.id
    temp_data[user_id] = {'team_name': team_name}
    
    if reg_mode == "paid":
        payment_text = (
            "💵 **পেমেন্ট তথ্য** 💵\n"
            "━━━━━━━━━━━━━━\n"
            f"বিকাশ/নগদ/রকেট (পার্সোনাল):\n`{PAYMENT_NUMBER}`\n\n"
            "টাকা পাঠিয়ে ট্রানজেকশন আইডি বা স্ক্রিনশট এখানে দিন।"
        )
        bot.send_message(message.chat.id, payment_text, parse_mode="Markdown")
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(user_id, message.from_user.username)
        bot.send_message(message.chat.id, f"✅ আপনার স্লট বুক হয়েছে!\n\n{get_slot_list_text(confirmed_teams)}", parse_mode="Markdown")

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data.get(user_id)
    if not team_info: return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট চেক:\nটিম: {team_info['team_name']}\nইউজার: @{message.from_user.username}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, f"তথ্য: {message.text}", reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ তথ্য পাঠানো হয়েছে। অ্যাডমিন চেক করে জানালে স্লটে নাম উঠবে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')) and call.from_user.id == ADMIN_ID)
def admin_decision(call):
    action, uid = call.data.split('_')
    uid = int(uid)
    if action == 'app':
        complete_registration(uid, "User")
        bot.send_message(uid, f"✅ আপনার স্লট কনফার্ম হয়েছে!\n\n{get_slot_list_text(confirmed_teams)}", parse_mode="Markdown")
        bot.edit_message_caption("অনুমোদিত ✅", call.message.chat.id, call.message.message_id) if call.message.photo else bot.edit_message_text("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ আপনার পেমেন্ট তথ্য সঠিক নয়।")

def complete_registration(uid, username):
    global confirmed_teams, last_full_list, registered_users
    if uid not in temp_data: return
    
    data = temp_data[uid]
    data['user_id'] = uid
    data['username'] = username if username else "NoUser"
    confirmed_teams.append(data)
    registered_users.add(uid)
    
    if len(confirmed_teams) == 12:
        bot.send_message(ADMIN_ID, f"🔥 ১২ জন পূর্ণ হয়েছে!\n\n{get_slot_list_text(confirmed_teams)}\nলিঙ্ক পাঠাতে /sendlink দিন।")
        last_full_list = list(confirmed_teams)
        confirmed_teams = [] 

# ৪. পাবলিক লিস্ট (গ্রুপে সবাই দেখতে পাবে)
@bot.message_handler(commands=['list'])
def show_list(message):
    if last_full_list:
        bot.send_message(message.chat.id, f"সর্বশেষ ১২ জনের লিস্ট:\n\n{get_slot_list_text(last_full_list)}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"বর্তমান রেজিস্ট্রেশন লিস্ট:\n\n{get_slot_list_text(confirmed_teams)}", parse_mode="Markdown")

# ৫. ইনবক্সে সাধারণদের জন্য গ্রুপ লিঙ্ক
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.from_user.id != ADMIN_ID)
def send_group_link(message):
    bot.send_message(message.chat.id, f"টুর্নামেন্ট রেজিস্ট্রেশন করতে গ্রুপে জয়েন করুন:\n{TOURNAMENT_GROUP_LINK}\n\nসেখানে গিয়ে /reg লিখুন।")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
