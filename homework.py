import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv
from requests.exceptions import (ConnectionError, HTTPError, MissingSchema,
                                 TooManyRedirects)
from telegram.ext import Updater

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRAKTIKUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 10
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
            response_json = response.json()
            return response_json
        else:
            raise HTTPError('Ошибка подключения')
    except json.decoder.JSONDecodeError:
        send_message(TELEGRAM_CHAT_ID, "N'est pas JSON")
        logger.error("N'est pas JSON")
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
    except TooManyRedirects:
        send_message(TELEGRAM_CHAT_ID, 'Превышено макс. кол-во redirect')
        logger.error('Превышено макс. кол-во redirect')


def check_response(response):
    """API запросы."""
    if not isinstance(response, dict):
        logger.error('Неправильный ответ API')
        raise TypeError('Неправильный ответ API')

    homework = response['homeworks']
    if len(homework) == 0:
        return[]

    if isinstance(homework, list):
        return homework
    else:
        raise KeyError('Домашнаяя работа не является списком')


def parse_status(homework):
    """Парс домашки."""
    print(homework)
    if 'homework_name' not in homework:
        logger.error('В ответе API не содержится ключ homework_name.')
        raise KeyError(
            'В ответе API не содержится ключ homework_name.'
        )

    if 'status' not in homework:
        logger.error('В ответе API не содержится ключ status.')
        raise KeyError('В ответе API не содержится ключ status.')

    if homework['status'] not in HOMEWORK_STATUSES:
        raise KeyError('ошибка статуса')

    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')
    verdict = HOMEWORK_STATUSES[homework_status]

    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    return message


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

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if len(homeworks) != 0:
                homework = homeworks[0]
                message = parse_status(homework)

            current_timestamp = response['current_date']
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
