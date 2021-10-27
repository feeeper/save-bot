import json

import boxsdk
import requests
from telegram import Bot as TelegramBot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.utils.request import Request

from config import Config


class SaverBot(TelegramBot):
    def __init__(self):
        self.config = Config()
        super().__init__(self.config.token, request=Request(con_pool_size=8))
        self.updater = Updater(bot=self, workers=4)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CommandHandler('login', self.login))

    def start(self, update: Update, context: CallbackContext):
        message_text: str = update.message.text
        message_parts: list[str] = message_text.split(' ')
        if len(message_parts) == 2:
            code: str = message_parts[1]
            access_token_url = 'https://api.box.com/oauth2/token'
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            params = {
                'client_id': self.config.client_id,
                'client_secret': self.config.client_token,
                'code': code,
                'grant_type': 'authorization_code'
            }
            req = requests.post(access_token_url, data=params, headers=headers)

            data = json.loads(req.text)

            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(
                self.config.client_id,
                self.config.client_token,
                access_token=data['access_token'],
                refresh_token=data['refresh_token'])
            box_client = boxsdk.Client(oauth)
            user = box_client.user().get()
            context.bot.send_message(chat_id=update.effective_chat.id, text=user.login)
        else:
            self.show_welcome_message(update, context)

    def login(self, update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'<a href="https://account.box.com/api/oauth2/authorize?client_id={self.config.client_id}&redirect_uri={self.config.redirect_url}&response_type=code">Connect to Box.com</a>',
                                 parse_mode='HTML')

    @staticmethod
    def show_welcome_message(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")

    def run(self):
        self.updater.start_polling()
