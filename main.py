import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- Koyeb Health Check Server ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- আপনার চূড়ান্ত কনফিগারেশন ---
API_TOKEN = '7960268103:AAGkoU1DF7igV2ZxQa_2V51VHTUlJv2Q96o'
TOURNAMENT_GROUP_LINK = "https://t.me/sgsgfsga"
ADMIN_ID = 7707686630  # আপনার দেওয়া আইডি বসানো হয়েছে
PAYMENT_NUMBER = "01704400069" # আপনার দেওয়া নম্বর

bot = telebot.TeleBot(API_TOKEN)

# ডাটাবেজ ভ্যারিয়েবল
reg_status = True  
reg_mode = "free"  
confirmed_teams = [] 
registered_phones = set() 
registered_users = set() 
temp_data = {}
last_full_list = []

print("বট সফলভাবে চালু হয়েছে...")

# --- সিকিউরিটি চেক ফাংশন ---
def is_admin(message):
    if message.from_user.id == ADMIN_ID:
        return True
    else:
        bot.reply_to(message, "❌ দুঃখিত, আপনি এই বটের অ্যাডমিন নন। আপনার জন্য এই কমান্ডটি অনুমোদিত নয়।")
        return False

# ১. অল ক্লিয়ার কমান্ড (সব ডাটা মুছতে)
@bot.message_handler(commands=['allclear'])
def clear_all_data(message):
    global confirmed_teams, registered_phones, registered_users, temp_data, last_full_list
    if is_admin(message):
        confirmed_teams = []
        registered_phones = set()
        registered_users = set()
        temp_data = {}
        last_full_list = []
        bot.send_message(ADMIN_ID, "♻️ টুর্নামেন্টের সব ডাটা সফলভাবে মুছে ফেলা হয়েছে। এখন সবাই নতুন করে রেজিস্ট্রেশন করতে পারবে।")

# ২. রেজিস্ট্রেশন অন/অফ কমান্ড
@bot.message_handler(commands=['on'])
def turn_on(message):
    global reg_status
    if is_admin(message):
        reg_status = True
        bot.send_message(ADMIN_ID, "✅ টুর্নামেন্ট রেজিস্ট্রেশন এখন চালু (ON)।")

@bot.message_handler(commands=['off'])
def turn_off(message):
    global reg_status
    if is_admin(message):
        reg_status = False
        bot.send_message(ADMIN_ID, "🛑 টুর্নামেন্ট রেজিস্ট্রেশন এখন বন্ধ (OFF)।")

# ৩. ফ্রি/পেইড মোড পরিবর্তন
@bot.message_handler(commands=['mode'])
def switch_mode(message):
    if is_admin(message):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("ফ্রি টুর্নামেন্ট 🆓", callback_data="set_free"),
                   types.InlineKeyboardButton("পেইড টুর্নামেন্ট 💰", callback_data="set_paid"))
        bot.send_message(ADMIN_ID, f"বর্তমান মোড: {reg_mode.upper()}\nমোড পরিবর্তন করতে নিচে ক্লিক করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def handle_mode_set(call):
    global reg_mode
    if call.from_user.id == ADMIN_ID:
        reg_mode = call.data.split('_')[1]
        bot.edit_message_text(f"✅ মোড সফলভাবে আপডেট হয়েছে: {reg_mode.upper()}", call.message.chat.id, call.message.message_id)

# ৪. রেজিস্ট্রেশন প্রসেস (গ্রুপে ম্যানেজারদের জন্য)
@bot.message_handler(commands=['reg'])
def start_reg(message):
    if not reg_status:
        bot.reply_to(message, "🛑 দুঃখিত, টুর্নামেন্ট রেজিস্ট্রেশন এখন বন্ধ আছে।")
        return
    if message.from_user.id in registered_users:
        bot.reply_to(message, "❌ আপনি ইতিমধ্যে এই টুর্নামেন্টে নাম লিখিয়েছেন। নতুন সুযোগ পেতে অ্যাডমিনের ঘোষণার অপেক্ষা করুন।")
        return

    msg = bot.send_message(message.chat.id, "🎮 আপনার **টিমের নাম** (Team Name) লিখুন:")
    bot.register_next_step_handler(msg, get_team_name)

def get_team_name(message):
    team_name = message.text
    temp_data[message.from_user.id] = {'team_name': team_name}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("ভেরিফাই করতে নম্বর দিন 📱", request_contact=True))
    msg = bot.send_message(message.chat.id, f"টিম: **{team_name}**\n\nএখন নিচের বাটনে ক্লিক করে আপনার নম্বর শেয়ার করুন। এতে আপনার স্লটটি ইউনিক থাকবে।", parse_mode="Markdown", reply_markup=markup)
    bot.register_next_step_handler(msg, verify_contact)

def verify_contact(message):
    if not message.contact:
        bot.send_message(message.chat.id, "❌ দয়া করে বাটন চেপে নম্বর দিন। আবার /reg করুন।")
        return
    phone = message.contact.phone_number
    if phone in registered_phones:
        bot.send_message(message.chat.id, "❌ এই নম্বরটি দিয়ে ইতিপূর্বে একবার রেজিস্ট্রেশন করা হয়েছে!")
        return
    
    temp_data[message.from_user.id]['phone'] = phone
    
    if reg_mode == "paid":
        payment_text = (
            "━━━━━━━━━━━━━━\n"
            "💵 **পেমেন্ট তথ্য (Paid Tournament)** 💵\n"
            "━━━━━━━━━━━━━━\n"
            "টুর্নামেন্টে আপনার স্লটটি নিশ্চিত করতে নিচে দেওয়া নম্বরে পেমেন্ট করুন:\n\n"
            f"🔸 **বিকাশ (পার্সোনাল):** `{PAYMENT_NUMBER}`\n"
            f"🔸 **নগদ (পার্সোনাল):** `{PAYMENT_NUMBER}`\n"
            f"🔸 **রকেট (পার্সোনাল):** `{PAYMENT_NUMBER}`\n\n"
            "⚠️ **টাকা পাঠানোর পর ট্রানজেকশন আইডি অথবা স্ক্রিনশট এখানে পাঠিয়ে দিন।**\n"
            "━━━━━━━━━━━━━━"
        )
        bot.send_message(message.chat.id, payment_text, parse_mode="Markdown", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(message.from_user.id, message.from_user.username)
        bot.send_message(message.chat.id, "✅ অভিনন্দন! আপনার ফ্রি স্লট বুক হয়েছে। অ্যাডমিন ভেরিফাই করলে গ্রুপ লিঙ্ক পাবেন।", reply_markup=types.ReplyKeyboardRemove())

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data[user_id]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}"))
    bot.send_message(ADMIN_ID, f"🔔 **নতুন পেমেন্ট অনুরোধ!**\n\nটিম: {team_info['team_name']}\nনম্বর: {team_info['phone']}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    else:
        bot.send_message(ADMIN_ID, f"তথ্য: {message.text}", reply_markup=markup)
    bot.send_message(user_id, "⏳ আপনার পেমেন্ট তথ্য জমা হয়েছে। অ্যাডমিন চেক করে আপনাকে মেসেজ দিবে।")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def admin_decision(call):
    if call.from_user.id == ADMIN_ID:
        action, uid = call.data.split('_')
        uid = int(uid)
        if action == 'app':
            complete_registration(uid, "User")
            bot.send_message(uid, "✅ অভিনন্দন! আপনার পেমেন্ট ভেরিফাই হয়েছে এবং স্লট কনফার্ম হয়েছে।")
            bot.edit_message_caption("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
        else:
            bot.send_message(uid, "❌ দুঃখিত, আপনার পেমেন্ট তথ্য সঠিক নয়। সঠিক স্লিপ দিয়ে আবার চেষ্টা করুন।")
            bot.answer_callback_query(call.id, "Rejected")

def complete_registration(uid, username):
    global confirmed_teams, last_full_list, registered_users, registered_phones
    data = temp_data[uid]
    data['user_id'] = uid
    data['username'] = username
    confirmed_teams.append(data)
    registered_users.add(uid)
    registered_phones.add(data['phone'])
    
    # অ্যাডমিনকে প্রতিটা রেজিস্ট্রেশন জানানো
    bot.send_message(ADMIN_ID, f"📝 নতুন টিম রেজিস্টার্ড: {data['team_name']} ({len(confirmed_teams)}/12)")

    if len(confirmed_teams) == 12:
        list_text = "🔥 **টুর্নামেন্টের ১২ জন ম্যানেজার পূর্ণ হয়েছে!**\n\n"
        for i, t in enumerate(confirmed_teams, 1):
            list_text += f"{i}. {t['team_name']} - @{t['username']}\n"
        bot.send_message(ADMIN_ID, list_text + "\nসবাইকে গ্রুপ লিঙ্ক পাঠাতে অ্যাডমিন ইনবক্সে **/sendlink** লিখুন।")
        last_full_list = list(confirmed_teams)
        confirmed_teams = [] # নতুন স্লটের জন্য রিসেট

@bot.message_handler(commands=['sendlink'])
def send_link(message):
    if is_admin(message):
        if not last_full_list:
            bot.send_message(ADMIN_ID, "❌ পাঠানোর মতো কোনো ১২ জনের লিস্ট নেই। আগে রেজিস্ট্রেশন পূর্ণ হতে দিন।")
            return
        for t in last_full_list:
            try: bot.send_message(t['user_id'], f"অভিনন্দন! আপনার টুর্নামেন্ট গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}\nজলদি জয়েন করুন।")
            except: pass
        bot.send_message(ADMIN_ID, "✅ সর্বশেষ ১২ জন ম্যানেজারকে গ্রুপ লিঙ্ক পাঠানো হয়েছে।")

@bot.message_handler(commands=['start'])
def start_bot(message):
    bot.reply_to(message, "স্বাগতম! ফ্রি ফায়ার টুর্নামেন্ট রেজিস্ট্রেশন করতে **/reg** লিখুন।")

if __name__ == "__main__":
    keep_alive() # Koyeb সার্ভারের জন্য
    bot.infinity_polling()
