import copy
from datetime import datetime
import zoneinfo
from typing import Any, DefaultDict, Dict, Optional
from telegram.ext import BasePersistence, PersistenceInput, PicklePersistence
from telegram.ext._utils.types import UD
import sqlite3


def init_db(name: str = 'save_bot.db') -> None:
    conn = sqlite3.connect(name)
    cursor = conn.cursor()

    cursor.execute('''CREATE TABLE chat_data
        (id                INTEGER PRIMARY KEY     AUTOINCREMENT,
         chat_id           INT     NOT NULL,
         active            INT     NOT NULL,
         registration_ts   INT, 
         access_token      CHAR(500),
         refresh_token     CHAR(500),
         box_folder_id     CHAR(500));''')


class SqlitePersistence(BasePersistence):
    def __init__(self, name: str='save_bot.db'):
        self.store_data = PersistenceInput(bot_data=False)
        self.conn = sqlite3.connect(name)
        self.cursor = self.conn.cursor()

    async def get_bot_data(self) -> Any:
        pass

    def update_bot_data(self, data) -> None:
        pass

    def refresh_bot_data(self, bot_data) -> None:
        pass

    async def get_chat_data(self) -> DefaultDict[int, Any]:
        data = self.cursor.execute('''SELECT * FROM chat_data''').fetchall()
        chat_data = {x[1]: dict(zip(['id', 'chat_id', 'active', 'registration_ts', 'access_token', 'refresh_token', 'box_folder_id'], x)) for x in data}
        return chat_data

    async def update_chat_data(self, chat_id: int, data: Any) -> None:
        should_update = False

        if isinstance(data, dict) and len(data) > 0:
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            box_folder_id = data['box_folder_id']            
            should_update = True

        if should_update:
            row = self.cursor.execute('''SELECT EXISTS(SELECT * FROM chat_data WHERE chat_id = ?)''', (chat_id,)).fetchone()
            if row[0] == 0:                
                ts = int(datetime.now(tz=zoneinfo.ZoneInfo('UTC')).timestamp())
                self.cursor.execute('''INSERT INTO chat_data
                                           (chat_id, active, registration_ts, access_token, refresh_token, box_folder_id)
                                       VALUES 
                                           (?, 1, ?, ?, ?, ?)''',
                    (chat_id, ts, access_token, refresh_token, box_folder_id))
            else:
                self.cursor.execute('''UPDATE chat_data
                                       SET
                                           access_token = ?,
                                           refresh_token = ?,
                                           box_folder_id = ?
                                       WHERE
                                           chat_id = ?''', (access_token, refresh_token, box_folder_id, chat_id))
            self.conn.commit()
                
        return super().update_chat_data(chat_id, data)

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> None:
        await self.update_chat_data(chat_id, chat_data)

    def get_user_data(self) -> DefaultDict[int, Any]:
        return copy.deepcopy(self.user_data)

    def update_user_data(self, user_id: int, data: Any) -> None:
        return super().update_user_data(user_id, data)

    def refresh_user_data(self, user_id: int, user_data: Any) -> None:
        return super().refresh_user_data(user_id, user_data)

    def get_callback_data(self) -> Optional[Any]:
        return super().get_callback_data()

    def update_callback_data(self, data: Any) -> None:
        return super().update_callback_data(data)

    def get_conversations(self, name: str) -> Any:
        return super().get_conversations(name)

    def update_conversation(self, name: str, key, new_state: Optional[object]) -> None:
        return super().update_conversation(name, key, new_state)

    def flush(self) -> None:
        return super().flush()

    async def drop_chat_data(self, chat_id: int) -> None:
        return await super().drop_chat_data(chat_id)

    async def drop_user_data(self, user_id: int) -> None:
        return await super().drop_user_data(user_id)

    async def get_user_data(self) -> Dict[int, UD]:
        return {}