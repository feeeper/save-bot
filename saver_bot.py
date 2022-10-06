import json

import boxsdk
from boxsdk.object.user import User as BoxUser
from boxsdk.object.folder import Folder as BoxFolder
from boxsdk.object.file import File as BoxFile

import requests
from telegram import Bot as TelegramBot, Update, ChatAction
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram.utils.request import Request

from config import Config


def get_save_bot_directory_name() -> str:
    return 'Save Bot Directory'


def get_success_registered_msg_text(login: str, box_folder_id: str) -> str:
    return  f'You\'ve been successfully registered with login {login}. I\'ve created a directory for savings called <a href="https://app.box.com/folder/{box_folder_id}">"Save Bot Directory"</a>'


def get_already_registered_msg_text(login: str, box_folder_id: str) -> str:
    return f'You\'ve been already registered with login {login}. The directory for savings called <a href="https://app.box.com/folder/{box_folder_id}">"Save Bot Directory"</a>'


def get_something_went_wrong_from_box_api_msg_text(box_exception: boxsdk.exception.BoxAPIException) -> str:
    return f'Something went wrong: {box_exception.message} (Code={box_exception.code})'


class SaverBot(TelegramBot):
    def __init__(self):
        self.config = Config()
        super().__init__(self.config.token, request=Request(con_pool_size=8))
        self.updater = Updater(bot=self, workers=4)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CommandHandler('start', self.start))
        self.dispatcher.add_handler(CommandHandler('register', self.register))

    def start(self, update: Update, context: CallbackContext):
        message_text: str = update.message.text
        message_parts: list[str] = message_text.split(' ')
        if len(message_parts) == 2:
            context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

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
            user: BoxUser = box_client.user().get()

            try:
                save_bot_directory: BoxFolder = box_client.root_folder().create_subfolder(get_save_bot_directory_name())
                
                context.bot.send_message(chat_id=update.effective_chat.id,
                                        text=get_success_registered_msg_text(user.login, save_bot_directory.object_id),
                                        parse_mode='HTML')
            except boxsdk.exception.BoxAPIException as box_exception:
                if box_exception.status == 409 and box_exception.code == 'item_name_in_use':
                    context_info = box_exception.context_info
                    conflicts = [x for x in context_info['conflicts'] if x['name'] == get_save_bot_directory_name()]
                    if len(conflicts) == 1:
                        save_bot_directory_object_id = conflicts[0]['id']                        
                        context.bot.send_message(chat_id=update.effective_chat.id,
                                                text=get_already_registered_msg_text(user.login, save_bot_directory_object_id),
                                                parse_mode='HTML')
                    else:
                        context.bot.send_message(chat_id=update.effective_chat.id,
                                            text=get_something_went_wrong_from_box_api_msg_text(box_exception),
                                            parse_mode='HTML')
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                            text=get_something_went_wrong_from_box_api_msg_text(box_exception),
                                            parse_mode='HTML')
        else:
            self.show_welcome_message(update, context)

    def register(self, update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text=f'<a href="https://account.box.com/api/oauth2/authorize?client_id={self.config.client_id}&redirect_uri={self.config.redirect_url}&response_type=code">Connect to Box.com</a>',
                                 parse_mode='HTML')

    @staticmethod
    def show_welcome_message(update: Update, context: CallbackContext):
        context.bot.send_message(chat_id=update.effective_chat.id, text='Save to Cloud bot')

    def run(self):
        self.updater.start_polling()
