import io

from telegram import Bot as TelegramBot, Update 
from telegram.ext import CommandHandler, CallbackContext, Application, BasePersistence, MessageHandler, filters
from telegram.ext import (
    CommandHandler,
    CallbackContext,
    Application,
    BasePersistence,
    MessageHandler,
    filters
)
from telegram.error import BadRequest as tgBadRequest

from config import Config
from box_cloud_provider import BoxProvider
from exceptions import (
    ItemNameInUseException,
    InternalException
)


class SaverBot(TelegramBot):
    def __init__(self, persistence: BasePersistence):
        config = Config()
        self.provider = BoxProvider(
            client_id=config.client_id,
            client_token=config.client_token,
            redirect_url=config.redirect_url)
        self.bot_token = config.token

        self.application = Application.builder().token(self.bot_token).persistence(persistence).build()
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(MessageHandler(filters=filters.ALL, callback=self.upload_file))


    async def start(self, update: Update, context: CallbackContext):
        message_parts: list[str] = update.message.text.split(' ')
        if len(message_parts) == 2:
            await self.register_user(update, context)
        else:
            await self.send_register_link(update, context)

    async def register_user(self, update, context):
        def _update_store_callback(access_token, refresh_token, directory_id) -> None:
            if access_token is None or refresh_token is None or directory_id is None:
                raise InternalException(ValueError(f'Some of required props are None: {access_token=}, {refresh_token=}, {directory_id=}'))
            context.chat_data['access_token'] = access_token
            context.chat_data['refresh_token'] = refresh_token
            context.chat_data['box_folder_id'] = directory_id

        try:
            code = update.message.text.split(' ')[1]
            user, access_token, refresh_token, save_bot_directory = self.provider.register_user(code, _update_store_callback)
            _update_store_callback(access_token, refresh_token, save_bot_directory.object_id)
            await update.message.reply_markdown(self.get_success_registered_msg_text(user.login, save_bot_directory.object_id))

        except ItemNameInUseException as item_name_in_use_ex:
            context.chat_data['box_folder_id'] = item_name_in_use_ex.item_id
            await update.message.reply_markdown(self.get_already_registered_msg_text(item_name_in_use_ex.user_login, item_name_in_use_ex.item_id))

        except InternalException as internal_ex:
            await update.message.reply_markdown(internal_ex.message)


    @staticmethod
    async def _send_no_document_passed_message(update: Update):
        await update.message.reply_text('Message does not contain any file. Please, try resend file one more time.')

    async def upload_file(self, update: Update, context: CallbackContext) -> None:
        if update.message.document is None:
            await self._send_no_document_passed_message(update)
            return
        
        if 'access_token' in context.chat_data:
            try:
                await update.message.reply_text(f'File {update.effective_message.document.file_name} is uploading to your {self.provider.name}.')
                uploaded_file = await self._upload_file(update, context)
                file_link = self.provider.get_file_link(uploaded_file.id, uploaded_file.name)
                await update.message.reply_markdown(f'{file_link} is now in your {self.provider.name}')
            except tgBadRequest as tg_exception:
                if tg_exception.message == 'File is too big':
                    await update.message.reply_text('Sorry, but the file is too big. Bot supports files less than 20 Mb only.')
                else:
                    await update.message.reply_text(f'Internal Telegram Error: {tg_exception.message}')
            except ItemNameInUseException as item_in_use_ex:
                existing_file_link = self.provider.get_file_link(item_in_use_ex.item_id, item_in_use_ex.item_name)
                await update.message.reply_markdown(f'File with the same name already exists: {existing_file_link}')
            except Exception as ex:
                await update.message.reply_text(f'Internal Error: {ex}')
        else:
            await update.message.reply_text(f'It seems like you have to connect to {self.provider.name}.')
            await self.send_register_link(update, context)

    async def _upload_file(self, update, context):
        access_token = context.chat_data['access_token']
        refresh_token = context.chat_data['refresh_token']
        folder_id = context.chat_data['box_folder_id']

        document = update.effective_message.document
        file = await self.application.bot.get_file(document.file_id)
        with io.BytesIO() as content:
            await file.download(out=content)
            uploaded_file = self.provider.upload_file(access_token, refresh_token, folder_id, content, document.file_name)
            return uploaded_file

    async def send_register_link(self, update: Update, context: CallbackContext):
        await update.message.reply_html(self.provider.get_registration_link())

    def get_success_registered_msg_text(self, login: str, box_folder_id: str) -> str:
        return  f'You\'ve been successfully registered with login {login}. I\'ve created a directory for savings called {self.provider.get_directory_link(box_folder_id, self.provider.directory_name)}'

    def get_already_registered_msg_text(self, login: str, box_folder_id: str) -> str:
        return f'You\'ve been already registered with login {login}. The directory for savings called {self.provider.get_directory_link(box_folder_id, self.provider.directory_name)}'

    def run(self):
        self.application.run_polling()
