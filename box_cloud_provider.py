import typing as t

import requests

import boxsdk
from boxsdk.object.user import User as BoxUser
from boxsdk.object.folder import Folder as BoxFolder
from boxsdk.object.file import File as BoxFile

from base_cloud_provider import BaseCloudProvider
from exceptions import (
    ItemNameInUseException,
    InternalException,
)


class BoxProvider(BaseCloudProvider):
    name: str = 'Box.com'

    def __init__(self, **kwargs) -> None:
        super().__init__()

        self.client_id = kwargs['client_id']
        self.client_token = kwargs['client_token']
        self.redirect_url = kwargs['redirect_url']

    def get_oauth_tokens(self, code: str) -> str:
        access_token_url = 'https://api.box.com/oauth2/token'
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_token,
            'code': code,
            'grant_type': 'authorization_code'
        }
        response = requests.post(access_token_url, data=params, headers=headers)

        json_response = response.json()
        access_token = json_response['access_token']
        refresh_token = json_response['refresh_token']

        return access_token, refresh_token

    def register_user(self, code: str, update_store_callback: t.Callable[[str, str, str], None]) -> str:
        access_token, refresh_token, save_bot_directory = None, None, None
        try:
            access_token, refresh_token = self.get_oauth_tokens(code)
            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(
                self.client_id,
                self.client_token,
                access_token=access_token,
                refresh_token=refresh_token)
            box_client = boxsdk.Client(oauth)
            user: BoxUser = box_client.user().get()
            save_bot_directory: BoxFolder = box_client.root_folder().create_subfolder(self.directory_name)
            return user, access_token, refresh_token, save_bot_directory
        except boxsdk.exception.BoxAPIException as box_exception:
            if box_exception.status == 409 and box_exception.code == 'item_name_in_use':
                context_info = box_exception.context_info
                conflicts = [x for x in context_info['conflicts'] if x['name'] == self.directory_name]
                if len(conflicts) == 1:
                    box_folder_id = conflicts[0]['id']
                    update_store_callback(access_token, refresh_token, box_folder_id)
                    raise ItemNameInUseException(user.login, box_folder_id, self.directory_name)
                else:
                    update_store_callback(access_token, refresh_token, save_bot_directory)
                    raise InternalException(box_exception)
        except Exception as ex:
            update_store_callback(access_token, refresh_token, save_bot_directory)
            raise InternalException(ex)

    def get_registration_link(self) -> str:
        return f'<a href="https://account.box.com/api/oauth2/authorize?client_id={self.client_id}&redirect_uri={self.redirect_url}&response_type=code">Connect to Box.com</a>'

    def get_directory_link(self, directory_id: str, directory_name: str) -> str:
        return f'[{directory_name}](https://app.box.com/file/{directory_id})'

    def get_file_link(self, file_id: str, file_name: str) -> str:
        return f'[{file_name}](https://app.box.com/file/{file_id})'

    def upload_file(self, access_token: str, refresh_token: str, folder_id: str, file, file_name: str) -> BoxFile:
        try:
            oauth: boxsdk.OAuth2 = boxsdk.OAuth2(self.client_id, self.client_token, access_token=access_token, refresh_token=refresh_token)
            box_client = boxsdk.Client(oauth)
            uploaded_file = box_client.folder(folder_id).upload_stream(file, file_name)
            return uploaded_file
        except boxsdk.exception.BoxAPIException as box_exception:
            if box_exception.status == 409 and box_exception.code == 'item_name_in_use':
                context_info = box_exception.context_info
                user: BoxUser = box_client.user().get()                
                file_id = context_info['conflicts']['id']
                file_name = context_info['conflicts']['name']
                raise ItemNameInUseException(user.login, file_id, file_name)
        except Exception as ex:
            raise InternalException(ex)