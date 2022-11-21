from datetime import datetime
import zoneinfo
from typing import Any, DefaultDict, Dict, Optional
from telegram.ext import BasePersistence, PersistenceInput
from telegram.ext._utils.types import UD, CD
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
        super().__init__(
            store_data=PersistenceInput(bot_data=False, user_data=False, callback_data=False),
            update_interval=1)
        self.conn = sqlite3.connect(name)
        self.cursor = self.conn.cursor()

    async def get_chat_data(self) -> DefaultDict[int, Any]:
        data = self.cursor.execute('''SELECT * FROM chat_data''').fetchall()
        chat_data = {x[1]: dict(zip(['id', 'chat_id', 'active', 'registration_ts', 'access_token', 'refresh_token', 'box_folder_id'], x)) for x in data}
        return chat_data

    async def update_chat_data(self, chat_id: int, data: CD) -> None:
        if isinstance(data, dict) and len(data) > 0:
            access_token = data['access_token']
            refresh_token = data['refresh_token']
            box_folder_id = data.get('box_folder_id', None)            

            is_chat_data_exists = self._chat_data_exists(chat_id)
            if is_chat_data_exists:
                self.cursor.execute('''UPDATE chat_data
                                       SET
                                           access_token = ?,
                                           refresh_token = ?,
                                           box_folder_id = ?
                                       WHERE
                                           chat_id = ?''', (access_token, refresh_token, box_folder_id, chat_id))
            else:
                ts = int(datetime.now(tz=zoneinfo.ZoneInfo('UTC')).timestamp())
                self.cursor.execute('''INSERT INTO chat_data
                                           (chat_id, active, registration_ts, access_token, refresh_token, box_folder_id)
                                       VALUES 
                                           (?, 1, ?, ?, ?, ?)''',
                    (chat_id, ts, access_token, refresh_token, box_folder_id))
                
            self.conn.commit()

    def _chat_data_exists(self, chat_id):
        row = self.cursor.execute('''SELECT EXISTS(SELECT * FROM chat_data WHERE chat_id = ?)''', (chat_id,)).fetchone()
        return row[0] > 0

    async def refresh_chat_data(self, chat_id: int, chat_data: Any) -> None:
        if isinstance(chat_data, dict):
            data = self.cursor.execute('''SELECT * FROM chat_data WHERE chat_id = ?''', (chat_id, )).fetchone()
            if data is not None:
                record = dict(zip(['id', 'chat_id', 'active', 'registration_ts', 'access_token', 'refresh_token', 'box_folder_id'], data))
                chat_data.update(record)

    async def drop_chat_data(self, chat_id: int) -> None:
        self.cursor.execute('''DELETE FROM chat_data WHERE chat_id = ?''', (chat_id, ))
        self.conn.commit()
    
    async def get_bot_data(self) -> Any:
        pass

    def update_bot_data(self, data) -> None:
        pass

    def refresh_bot_data(self, bot_data) -> None:
        pass

    def get_user_data(self) -> DefaultDict[int, Any]:
        pass

    def update_user_data(self, user_id: int, data: Any) -> None:
        pass

    def refresh_user_data(self, user_id: int, user_data: Any) -> None:
        pass

    def get_callback_data(self) -> Optional[Any]:
        pass

    def update_callback_data(self, data: Any) -> None:
        pass

    def get_conversations(self, name: str) -> Any:
        pass

    def update_conversation(self, name: str, key, new_state: Optional[object]) -> None:
        pass

    def flush(self) -> None:
        self.conn.close()  

    async def drop_user_data(self, user_id: int) -> None:
        pass

    async def get_user_data(self) -> Dict[int, UD]:
        pass