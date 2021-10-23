from telegram.ext import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext import CommandHandler
from config import Config
import requests
import json
import boxsdk


config: Config = Config()

client_secret: str = config.client_token
client_id: str = config.client_id
redirect_url: str = 'http://localhost:8000'

token = config.token
updater = Updater(token=token, use_context=True)
dispatcher = updater.dispatcher

def start(update: Update, context: CallbackContext):
    message_text: str = update.message.text
    message_parts: list[str] = message_text.split(' ')
    if len(message_parts) == 2:
        code: str = message_parts[1]
        access_token_url = 'https://api.box.com/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = {
            'client_id': client_id,
            'client_secret': client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        req = requests.post(access_token_url, data=params, headers=headers)

        data = json.loads(req.text)

        oauth: boxsdk.OAuth2 = boxsdk.OAuth2(
            client_id,
            client_secret,
            access_token=data['access_token'],
            refresh_token=data['refresh_token'])
        box_client = boxsdk.Client(oauth)        
        user = box_client.user().get()
        context.bot.send_message(chat_id=update.effective_chat.id, text=user.login)
    else:
        show_welcome_message(update, context)

def login(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text=f'<a href="https://account.box.com/api/oauth2/authorize?client_id={client_id}&redirect_uri={redirect_url}&response_type=code">Connect to Box.com</a>', parse_mode='HTML')

def show_welcome_message(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

start_handler = CommandHandler('start', start)
login_handler = CommandHandler('login', login)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(login_handler)

updater.start_polling()
