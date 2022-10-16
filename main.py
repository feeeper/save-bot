from email.policy import default
from saver_bot import SaverBot
from sqlite_persistence import SqlitePersistence, init_db
from telegram.ext import PicklePersistence
import click


def init_database(db: str) -> None:
    init_db(db)


@click.command()
@click.option('--mode', default='run', help='Execution mode: "run" or "init"')
@click.option('--db', default='save_bot.db')
def main(mode: str = 'run', db: str = 'save_bot.db') -> None:
    if mode == 'run':
        bot = SaverBot(persistence=SqlitePersistence(db))
        bot.run()
    elif mode == 'init':
        print(f'init {db} db')
        init_database(db)


if __name__ == '__main__':
    main()
