import typing as t

class BaseCloudProvider:
    directory_name: str = 'Save Bot Directory'
    name: str = 'base'

    def __init__(self, **kwargs) -> None:
        ...

    def get_registration_link(self) -> str:
        ...

    def get_directory_link(self, directory_id: str) -> str:
        ...

    def get_file_link(self, file_id: str, file_name: str) -> str:
        ...

    def get_oauth_tokens(self, code: str) -> str:
        ...

    def register_user(self, code: str, update_store_callback: t.Callable[[str, str, str], None]) -> str:
        ...

    def upload_file(self, access_token: str, refresh_token: str, file) -> t.Any:
        ...

    def search(self, access_token: str, refresh_token: str, folder_id: str, query: str) -> t.Any:
        ...