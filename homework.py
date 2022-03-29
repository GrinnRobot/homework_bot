import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, MissingSchema
from telegram.ext import Updater

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

upd = Updater(token=TELEGRAM_TOKEN, use_context=True)

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)

logger = logging.getLogger()


def send_message(bot, message):
    """Отправление сообщения боту."""
    chat_id = TELEGRAM_CHAT_ID
    bot.send_message(chat_id, message)
    logger.info(f'Функция {send_message.__name__} работает правильно')
    if message['status'] not in HOMEWORK_STATUSES.values():
        logger.debug(
            'отсутствие в ответах обновленных статусов'
        )
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Получение API запроса."""
    try:
        params = {'from_date': current_timestamp}
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise ValueError('Статус код не 200"')
    except ConnectionError:
        logger.critical(f'Нет доступа к "{ENDPOINT}"')
    except MissingSchema:
        chat_id = TELEGRAM_CHAT_ID
        bot = telegram.Bot(token=f'{TELEGRAM_TOKEN}')
        bot.send_message(chat_id, '"ENDPOINT" указан не корректно')
        logger.error('"ENDPOINT" указан не корректно')
    except NameError:
        chat_id = TELEGRAM_CHAT_ID
        bot = telegram.Bot(token=f'{TELEGRAM_TOKEN}')
        bot.send_message(chat_id, '"ENDPOINT" не указан')
        logger.error('"ENDPOINT" не указан')


def check_response(response):
    """API запросы."""
    if not isinstance(response, dict):
        raise TypeError('Неправильный ответ API')

    homeworks = response.get('homeworks')
    if isinstance(homeworks, list):
        return homeworks
    else:
        raise KeyError('Отсутствует домашные работы')


def parse_status(homework):
    """Парс домашки."""
    status = homework.get('status')
    if status is None:
        raise KeyError(
            'Отсутствует status'
        )

    name = homework.get('homework_name')
    if name is None:
        raise KeyError(
            'Отсутствует homework_name'
        )

    status_desc = HOMEWORK_STATUSES.get(status)
    if status_desc is not None:
        return f'Изменился статус проверки работы "{name}": {status_desc}'
    else:
        raise ValueError('Некорректный статус работы')


def check_tokens():
    """Проверка доступности переменных окружения."""
    token_list = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID,
    ]
    for token in token_list:
        try:
            if token is None:
                return False
        except Exception as error:
            logging.error(f'Переменные окружения не доступны: {error}')
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
                time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
