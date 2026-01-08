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
registered_phones = set() 
registered_users = set() 
temp_data = {}
last_full_list = []

# --- স্লট লিস্ট তৈরি করার ফাংশন ---
def get_slot_list_text():
    text = "🏆 **Tournament Slot Status (Max 12)** 🏆\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    for i in range(1, 13):
        if i <= len(confirmed_teams):
            team = confirmed_teams[i-1]
            text += f"✅ Slot {i}: {team['team_name']} (@{team['username']})\n"
        else:
            text += f"⬜ Slot {i}: খালি\n"
    text += "━━━━━━━━━━━━━━━━━━━━\n"
    return text

# --- সিকিউরিটি চেক (শুধুমাত্র অ্যাডমিন ইনবক্স) ---
def is_admin_private(message):
    return message.chat.type == 'private' and message.from_user.id == ADMIN_ID

# ১. অল ক্লিয়ার (অ্যাডমিন ইনবক্স)
@bot.message_handler(commands=['allclear'])
def clear_all_data(message):
    global confirmed_teams, registered_phones, registered_users, temp_data, last_full_list
    if is_admin_private(message):
        confirmed_teams = []
        registered_phones = set()
        registered_users = set()
        temp_data = {}
        last_full_list = []
        bot.send_message(ADMIN_ID, "♻️ সব ডাটা মুছে ফেলা হয়েছে। নতুন টুর্নামেন্ট শুরু করার জন্য প্রস্তুত!")

# ২. অন/অফ এবং মোড (অ্যাডমিন ইনবক্স)
@bot.message_handler(commands=['on'])
def turn_on(message):
    global reg_status
    if is_admin_private(message):
        reg_status = True
        bot.send_message(ADMIN_ID, "✅ রেজিস্ট্রেশন এখন চালু (ON)।")

@bot.message_handler(commands=['off'])
def turn_off(message):
    global reg_status
    if is_admin_private(message):
        reg_status = False
        bot.send_message(ADMIN_ID, "🛑 রেজিস্ট্রেশন এখন বন্ধ (OFF)।")

@bot.message_handler(commands=['mode'])
def switch_mode(message):
    if is_admin_private(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Free Mode 🆓", callback_data="set_free"),
                   types.InlineKeyboardButton("Paid Mode 💰", callback_data="set_paid"))
        bot.send_message(ADMIN_ID, f"বর্তমান মোড: {reg_mode.upper()}\nপরিবর্তন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def handle_mode_set(call):
    global reg_mode
    if call.from_user.id == ADMIN_ID:
        reg_mode = call.data.split('_')[1]
        bot.edit_message_text(f"✅ মোড পরিবর্তন হয়েছে: {reg_mode.upper()}", call.message.chat.id, call.message.message_id)

# ৩. গ্রুপ রেজিস্ট্রেশন এবং স্লট লিস্ট
@bot.message_handler(commands=['reg'])
def start_reg(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ রেজিস্ট্রেশন করার জন্য টুর্নামেন্ট গ্রুপে মেসেজ দিন।")
        return

    if not reg_status:
        bot.reply_to(message, "🛑 দুঃখিত, এখন রেজিস্ট্রেশন বন্ধ আছে।")
        return
    
    if message.from_user.id in registered_users:
        bot.reply_to(message, "❌ আপনি ইতিমধ্যে এই স্লট লিস্টে আছেন!")
        return

    if len(confirmed_teams) >= 12:
        bot.reply_to(message, "🚫 ১২টি স্লট পূর্ণ হয়ে গেছে! নতুন টুর্নামেন্টের অপেক্ষা করুন।")
        return

    current_slot = len(confirmed_teams) + 1
    msg = bot.send_message(message.chat.id, f"🎮 **টিম {current_slot}/12** এর জন্য নাম লিখুন:")
    bot.register_next_step_handler(msg, get_team_name)

def get_team_name(message):
    team_name = message.text
    temp_data[message.from_user.id] = {'team_name': team_name}
    
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("নম্বর শেয়ার করুন 📱", request_contact=True))
    
    bot.send_message(message.chat.id, f"টিম: {team_name}\nএখন আপনার নম্বরটি ভেরিফাই করতে বাটনে ক্লিক করুন:", reply_markup=markup)
    bot.register_next_step_handler(message, verify_contact)

def verify_contact(message):
    if not message.contact:
        bot.send_message(message.chat.id, "❌ বাটন ব্যবহার করুন। আবার /reg করুন।")
        return
    phone = message.contact.phone_number
    if phone in registered_phones:
        bot.send_message(message.chat.id, "❌ এই নম্বরটি ইতিপূর্বে ব্যবহার করা হয়েছে!")
        return
    
    temp_data[message.from_user.id]['phone'] = phone

    if reg_mode == "paid":
        payment_text = (
            f"💰 **পেইড টুর্নামেন্ট পেমেন্ট** 💰\n"
            "━━━━━━━━━━━━━━\n"
            f"বিকাশ/নগদ/রকেট (পার্সোনাল):\n`{PAYMENT_NUMBER}`\n\n"
            "টাকা পাঠিয়ে ট্রানজেকশন আইডি বা স্ক্রিনশট এখানে দিন।"
        )
        bot.send_message(message.chat.id, payment_text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(message.from_user.id, message.from_user.username)
        bot.send_message(message.chat.id, f"✅ অভিনন্দন! স্লট বুক হয়েছে।\n\n{get_slot_list_text()}", parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data[user_id]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}"))
    
    bot.send_message(ADMIN_ID, f"🔔 নতুন পেমেন্ট অনুরোধ:\nটিম: {team_info['team_name']}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(message.chat.id, "⏳ আপনার তথ্য পাঠানো হয়েছে। অ্যাডমিন চেক করলে স্লট লিস্টে নাম উঠবে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def admin_decision(call):
    if call.from_user.id == ADMIN_ID:
        action, uid = call.data.split('_')
        uid = int(uid)
        if action == 'app':
            complete_registration(uid, "User")
            bot.send_message(uid, f"✅ আপনার স্লট কনফার্ম হয়েছে!\n\n{get_slot_list_text()}", parse_mode="Markdown")
            bot.edit_message_caption("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(uid, "❌ আপনার পেমেন্ট তথ্য সঠিক নয়।")

def complete_registration(uid, username):
    global confirmed_teams, last_full_list, registered_users, registered_phones
    data = temp_data[uid]
    data['user_id'] = uid
    data['username'] = username if username else "NoUser"
    confirmed_teams.append(data)
    registered_users.add(uid)
    registered_phones.add(data['phone'])
    
    if len(confirmed_teams) == 12:
        bot.send_message(ADMIN_ID, f"🔥 ১২ জন পূর্ণ হয়েছে!\n\n{get_slot_list_text()}\nলিঙ্ক পাঠাতে /sendlink দিন।", parse_mode="Markdown")
        last_full_list = list(confirmed_teams)
        confirmed_teams = [] 

# ৪. স্লট লিস্ট দেখার কমান্ড (গ্রুপে সবাই দেখতে পারবে)
@bot.message_handler(commands=['list'])
def show_list(message):
    bot.send_message(message.chat.id, get_slot_list_text(), parse_mode="Markdown")

@bot.message_handler(commands=['sendlink'])
def send_link(message):
    if is_admin_private(message):
        if not last_full_list:
            bot.send_message(ADMIN_ID, "❌ কোনো লিস্ট পাওয়া যায়নি।")
            return
        for t in last_full_list:
            try: bot.send_message(t['user_id'], f"অভিনন্দন! টুর্নামেন্ট গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ ১২ জন ম্যানেজারকে লিঙ্ক পাঠানো হয়েছে।")

@bot.message_handler(commands=['start'])
def start_bot(message):
    bot.reply_to(message, "স্বাগতম! রেজিস্ট্রেশন করতে গ্রুপে গিয়ে /reg লিখুন।")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
