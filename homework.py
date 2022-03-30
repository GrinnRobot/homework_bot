import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, HTTPError, MissingSchema
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
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Функция {send_message.__name__} работает правильно')
    except telegram.TelegramError:
        logger.info(f'Функция {send_message.__name__} работает ошибочно')


def get_api_answer(current_timestamp):
    """Запрос API."""
    try:
        params = {'from_date': current_timestamp}
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
        if response.status_code == HTTPStatus.OK:
            response = response.json()
            return response
        else:
            raise HTTPError('Ошибка подключения')
    
    except ConnectionError:
        logger.critical(f'Нет доступа к "{ENDPOINT}"')
    except MissingSchema:
        send_message(TELEGRAM_CHAT_ID, '"ENDPOINT" указан не корректно')
        logger.error('"ENDPOINT" указан не корректно')
    except NameError:
        send_message(TELEGRAM_CHAT_ID, '"ENDPOINT" не указан')
        logger.error('"ENDPOINT" не указан')
    except TimeoutError:
        send_message(TELEGRAM_CHAT_ID, 'Время подключения истекло')
        logger.error('Время подключения истекло')


def check_response(response):
    """API запросы."""
    if not isinstance(response, dict):
        raise TypeError('Неправильный ответ API')

    homework = response.get('homeworks')
    if isinstance(homework, list):
        return homework
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
        if token is None:
            return False
    return True


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    er = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework is not None:
                message = parse_status(homework)
                send_message(bot, message)
            
            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message != er and send_message(bot, message):
                er = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
