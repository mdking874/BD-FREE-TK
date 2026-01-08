import telebot
from telebot import types
from flask import Flask
from threading import Thread

# --- Koyeb-এর জন্য Fake Web Server ---
app = Flask('')
@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- আপনার বটের তথ্য ---
API_TOKEN = '7960268103:AAGkoU1DF7igV2ZxQa_2V51VHTUlJv2Q96o'
TOURNAMENT_GROUP_LINK = "https://t.me/sgsgfsga"
ADMIN_ID = 7707686630  # <--- এখানে আপনার আইডি দিন ( @userinfobot থেকে নিয়ে)

bot = telebot.TeleBot(API_TOKEN)

# ডাটাবেজ
reg_status = True  
reg_mode = "free"  
confirmed_teams = [] 
registered_phones = set() 
temp_data = {}
last_full_list = []

@bot.message_handler(commands=['start'])
def welcome(message):
    bot.reply_to(message, "স্বাগতম! টুর্নামেন্টে রেজিস্ট্রেশন করতে /reg লিখুন।\n\nঅ্যাডমিন মোড পরিবর্তন করতে /mode ব্যবহার করুন।")

@bot.message_handler(commands=['on'])
def turn_on(message):
    global reg_status
    if message.from_user.id == ADMIN_ID:
        reg_status = True
        bot.send_message(ADMIN_ID, "✅ রেজিস্ট্রেশন চালু করা হয়েছে।")

@bot.message_handler(commands=['off'])
def turn_off(message):
    global reg_status
    if message.from_user.id == ADMIN_ID:
        reg_status = False
        bot.send_message(ADMIN_ID, "🛑 রেজিস্ট্রেশন বন্ধ করা হয়েছে।")

@bot.message_handler(commands=['mode'])
def switch_mode(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Free Mode", callback_data="set_free"),
                   types.InlineKeyboardButton("Paid Mode", callback_data="set_paid"))
        bot.send_message(ADMIN_ID, f"বর্তমান মোড: {reg_mode.upper()}\nমোড পরিবর্তন করুন:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('set_'))
def handle_mode_set(call):
    global reg_mode
    reg_mode = call.data.split('_')[1]
    bot.edit_message_text(f"✅ মোড পরিবর্তন হয়ে {reg_mode.upper()} হয়েছে।", call.message.chat.id, call.message.message_id)

@bot.message_handler(commands=['reg'])
def start_reg(message):
    if not reg_status:
        bot.reply_to(message, "🛑 দুঃখিত, রেজিস্ট্রেশন এখন বন্ধ আছে।")
        return
    if message.from_user.id in [t['user_id'] for t in confirmed_teams]:
        bot.reply_to(message, "❌ আপনি ইতিমধ্যে এই ১২ জনের স্লটে আছেন।")
        return

    msg = bot.send_message(message.chat.id, "আপনার টিমের নাম লিখুন:")
    bot.register_next_step_handler(msg, get_team_name)

def get_team_name(message):
    team_name = message.text
    temp_data[message.from_user.id] = {'team_name': team_name}
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add(types.KeyboardButton("নম্বর শেয়ার করুন 📱", request_contact=True))
    msg = bot.send_message(message.chat.id, "বাটনে ক্লিক করে আপনার নম্বর ভেরিফাই করুন:", reply_markup=markup)
    bot.register_next_step_handler(msg, verify_contact)

def verify_contact(message):
    if not message.contact:
        bot.send_message(message.chat.id, "❌ বাটন ব্যবহার করুন। আবার /reg লিখুন।")
        return
    phone = message.contact.phone_number
    if phone in registered_phones:
        bot.send_message(message.chat.id, "❌ এই নম্বরটি ইতিমধ্যে ব্যবহৃত হয়েছে!")
        return
    temp_data[message.from_user.id]['phone'] = phone
    if reg_mode == "paid":
        bot.send_message(message.chat.id, "💰 টাকা পাঠিয়ে স্লিপের ছবি দিন।", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, get_payment_proof)
    else:
        complete_registration(message.from_user.id, message.from_user.username)
        bot.send_message(message.chat.id, "✅ আপনার নাম রেজিস্ট্রেশন হয়েছে!", reply_markup=types.ReplyKeyboardRemove())

def get_payment_proof(message):
    user_id = message.from_user.id
    team_info = temp_data[user_id]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{user_id}"),
               types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{user_id}"))
    bot.send_message(ADMIN_ID, f"🔔 পেমেন্ট চেক:\nটিম: {team_info['team_name']}")
    if message.photo:
        bot.send_photo(ADMIN_ID, message.photo[-1].file_id, reply_markup=markup)
    bot.send_message(user_id, "⏳ চেক করা হচ্ছে...")

@bot.callback_query_handler(func=lambda call: call.data.startswith(('app_', 'rej_')))
def admin_decision(call):
    action, uid = call.data.split('_')
    uid = int(uid)
    if action == 'app':
        complete_registration(uid, "User")
        bot.send_message(uid, "✅ আপনার স্লট কনফার্ম হয়েছে!")
        bot.edit_message_caption("অনুমোদিত ✅", call.message.chat.id, call.message.message_id)
    else:
        bot.send_message(uid, "❌ পেমেন্ট বাতিল হয়েছে।")

def complete_registration(uid, username):
    global confirmed_teams, last_full_list
    data = temp_data[uid]
    data['user_id'] = uid
    data['username'] = username
    confirmed_teams.append(data)
    registered_phones.add(data['phone'])
    
    if len(confirmed_teams) == 12:
        list_text = "🔥 টুর্নামেন্টের ১২ জন পূর্ণ হয়েছে!\n\n"
        for i, t in enumerate(confirmed_teams, 1):
            list_text += f"{i}. {t['team_name']} (@{t['username']})\n"
        bot.send_message(ADMIN_ID, list_text + "\nসবাইকে লিঙ্ক পাঠাতে /sendlink লিখুন।")
        last_full_list = list(confirmed_teams)
        confirmed_teams = [] # স্লট রিসেট

@bot.message_handler(commands=['sendlink'])
def send_link(message):
    if message.from_user.id == ADMIN_ID:
        for t in last_full_list:
            try: bot.send_message(t['user_id'], f"গ্রুপ লিঙ্ক: {TOURNAMENT_GROUP_LINK}")
            except: pass
        bot.send_message(ADMIN_ID, "✅ লিঙ্ক পাঠানো হয়েছে।")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
