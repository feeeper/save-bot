import io
import json

import boxsdk
from boxsdk.object.user import User as BoxUser
from boxsdk.object.folder import Folder as BoxFolder


import requests
from telegram import Bot as TelegramBot, Update 
from telegram.ext import CommandHandler, CallbackContext, Application, BasePersistence, MessageHandler, filters


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
    def __init__(self, persistence: BasePersistence):
        self.config = Config()
        self.application = Application.builder().token(self.config.token).persistence(persistence).build()
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('register', self.register))
        self.application.add_handler(MessageHandler(filters=filters.ALL, callback=self.save_item))


    async def start(self, update: Update, context: CallbackContext):
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
            user: BoxUser = box_client.user().get()
            self.application.chat_data[update.message.chat_id]['access_token'] = data['access_token']
            self.application.chat_data[update.message.chat_id]['refresh_token'] = data['refresh_token']

            try:
                save_bot_directory: BoxFolder = box_client.root_folder().create_subfolder(get_save_bot_directory_name())
                self.application.chat_data[update.message.chat_id]['box_folder_id'] = save_bot_directory.object_id
                
                await update.message.reply_html(get_success_registered_msg_text(user.login, save_bot_directory.object_id))


            except boxsdk.exception.BoxAPIException as box_exception:
                if box_exception.status == 409 and box_exception.code == 'item_name_in_use':
                    context_info = box_exception.context_info
                    conflicts = [x for x in context_info['conflicts'] if x['name'] == get_save_bot_directory_name()]
                    if len(conflicts) == 1:
                        save_bot_directory_object_id = conflicts[0]['id']                        
                        await update.message.reply_html(get_already_registered_msg_text(user.login, save_bot_directory_object_id))


                    else:
                        await update.message.reply_html(get_something_went_wrong_from_box_api_msg_text(box_exception))


                else:
                    await update.message.reply_html(get_something_went_wrong_from_box_api_msg_text(box_exception))


        else:
            await self.show_welcome_message(update, context)

    async def register(self, update: Update, context: CallbackContext):
        await update.message.reply_html(f'<a href="https://account.box.com/api/oauth2/authorize?client_id={self.config.client_id}&redirect_uri={self.config.redirect_url}&response_type=code">Connect to Box.com</a>')



    @staticmethod
    async def show_welcome_message(update: Update, context: CallbackContext):
        await update.message.reply_text('Save to Cloud bot')

    async def save_item(self, update: Update, context: CallbackContext) -> None:
        if update.message.chat_id in self.application.chat_data and 'access_token' in self.application.chat_data[update.message.chat_id]:
            access_token = self.application.chat_data[update.message.chat_id]['access_token']
            refresh_token = self.application.chat_data[update.message.chat_id]['access_token']
            folder_id = self.application.chat_data[update.message.chat_id]['box_folder_id']
            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(
                self.config.client_id,
                self.config.client_token,
                access_token=access_token,
                refresh_token=refresh_token)
            box_client = boxsdk.Client(oauth)

            document = update.effective_message.document
            file = await self.application.bot.get_file(document.file_id)

            with io.BytesIO() as content:
                await file.download(out=content)
                uploaded_file = box_client.folder(folder_id).upload_stream(content, document.file_name)
                await update.message.reply_markdown(f'[{uploaded_file.name}](https://app.box.com/file/{uploaded_file.id}) is now in you Box')

    def run(self):
        self.application.run_polling()
