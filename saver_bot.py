import io
import json

import boxsdk
from boxsdk.object.user import User as BoxUser
from boxsdk.object.folder import Folder as BoxFolder


import requests
from telegram import Bot as TelegramBot, Update
from telegram.ext import CommandHandler, CallbackContext, Application, BasePersistence, MessageHandler, filters
from telegram.error import BadRequest as tgBadRequest


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
        config = Config()
        self.client_id = config.client_id
        self.client_token = config.client_token
        self.redirect_url = config.redirect_url
        self.bot_token = config.token

        self.application = Application.builder().token(self.bot_token).persistence(persistence).build()
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('register', self.register))
        self.application.add_handler(MessageHandler(filters=filters.ALL, callback=self.upload_file))


    async def start(self, update: Update, context: CallbackContext):
        message_text: str = update.message.text
        message_parts: list[str] = message_text.split(' ')
        if len(message_parts) == 2:
            code: str = message_parts[1]
            access_token_url = 'https://api.box.com/oauth2/token'
            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            params = {
                'client_id': self.client_id,
                'client_secret': self.client_token,
                'code': code,
                'grant_type': 'authorization_code'
            }
            req = requests.post(access_token_url, data=params, headers=headers)

            data = json.loads(req.text)
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            self.application.chat_data[update.message.chat_id]['access_token'] = access_token
            self.application.chat_data[update.message.chat_id]['refresh_token'] = refresh_token

            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(self.client_id, self.client_token, access_token=access_token, refresh_token=refresh_token)
            box_client = boxsdk.Client(oauth)
            user: BoxUser = box_client.user().get()            

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
                        self.application.chat_data[update.message.chat_id]['box_folder_id'] = save_bot_directory_object_id
                        await update.message.reply_html(get_already_registered_msg_text(user.login, save_bot_directory_object_id))
                    else:
                        await update.message.reply_html(get_something_went_wrong_from_box_api_msg_text(box_exception))
                else:
                    await update.message.reply_html(get_something_went_wrong_from_box_api_msg_text(box_exception))
        else:
            await self.show_welcome_message(update, context)

    async def register(self, update: Update, context: CallbackContext):
        await update.message.reply_html(f'<a href="https://account.box.com/api/oauth2/authorize?client_id={self.client_id}&redirect_uri={self.redirect_url}&response_type=code">Connect to Box.com</a>')

    @staticmethod
    async def show_welcome_message(update: Update, context: CallbackContext):
        await update.message.reply_text('Save to Cloud bot')

    @staticmethod
    async def _send_no_document_passed_message(update: Update):
        await update.message.reply_text('Message does not contain any file. Please, try resend file one more time.')

    async def upload_file(self, update: Update, context: CallbackContext) -> None:
        if update.message.document is None:
            await self._send_no_document_passed_message(update)
            return
            
        if update.message.chat_id in self.application.chat_data and 'access_token' in self.application.chat_data[update.message.chat_id]:
            access_token = self.application.chat_data[update.message.chat_id]['access_token']
            refresh_token = self.application.chat_data[update.message.chat_id]['access_token']
            folder_id = self.application.chat_data[update.message.chat_id]['box_folder_id']
            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(self.client_id, self.client_token, access_token=access_token, refresh_token=refresh_token)
            box_client = boxsdk.Client(oauth)

            try:
                await update.message.reply_text(f'File {update.effective_message.document.file_name} is uploading to your Box.')
                document = update.effective_message.document
                file = await self.application.bot.get_file(document.file_id)
                with io.BytesIO() as content:
                    await file.download(out=content)
                    uploaded_file = box_client.folder(folder_id).upload_stream(content, document.file_name)
                    await update.message.reply_markdown(f'[{uploaded_file.name}](https://app.box.com/file/{uploaded_file.id}) is now in your Box')
            except tgBadRequest as tg_exception:
                if tg_exception.message == 'File is too big':
                    await update.message.reply_text('Sorry, but the file is too big. Bot supports files less than 20 Mb only.')
                else:
                    await update.message.reply_text(f'Internal Telegram Error: {tg_exception.message}')
            except boxsdk.exception.BoxAPIException as box_exception:
                if box_exception.status == 409 and box_exception.code == 'item_name_in_use':
                    context_info = box_exception.context_info
                    existing_file_link = f'[{context_info["conflicts"]["name"]}](https://app.box.com/file/{context_info["conflicts"]["id"]})'
                    await update.message.reply_markdown(f'File with the same name already exists: {existing_file_link}')
            except Exception as ex:
                await update.message.reply_text(f'Internal Error: {ex.message}')

    def run(self):
        self.application.run_polling()
