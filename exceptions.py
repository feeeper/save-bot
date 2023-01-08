import typing as t


class ItemNameInUseException(Exception):
    def __init__(self, user_login: str, item_id: str, item_name: str) -> None:
        self.user_login = user_login
        self.item_id = item_id
        self.item_name = item_name


class InternalException(Exception):
    def __init__(self, ex: Exception) -> None:
        self.message = f'Something went wrong: {ex}'
