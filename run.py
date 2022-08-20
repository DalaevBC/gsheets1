import json
import os
import time
from pprint import pprint

import requests

import apiclient
import httplib2
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build

from db_models import GoogleSheeds, db


CREDENTIALS_FILE = 'creds.json'

spreadsheet_id = '1MYzVuevsxyzgUqZF4zYV6SA-e7KPbgFSXSfzf1WN4a4'

# Авторизуемся и получаем service — экземпляр доступа к API
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())


service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)
drive_service = build('drive', 'v3', http=httpAuth)


def check_changes():
    """
    Текущий токен страницы хранится в файле 'config_holder.json'
    Если новый токен отличается от старого - значит изменения были - возвращаем True
    """
    with open('config_holder.json', 'r') as file:
        config = json.load(file)
        start_token = config.get('startPageToken')

    page_token = start_token
    were_changes_in_a_file = False
    start_page_token = start_token

    while page_token is not None:
        start_page_token = drive_service.changes().getStartPageToken().execute().get('startPageToken')

        response = drive_service.changes().list(
            pageToken=page_token,
            spaces='drive',
        ).execute()
        print('response =', response)

        for change in response.get('changes'):
            file_id = change.get("fileId")
            if file_id == spreadsheet_id:
                were_changes_in_a_file = True
        if 'newStartPageToken' in response:
            start_page_token = response.get('newStartPageToken')

        time.sleep(60)

        page_token = response.get('nextPageToken')

    if start_page_token != start_token: # перезиписываем токен
        with open('config_holder.json', 'w') as config_file:
            json.dump({
                "spreadsheetId": spreadsheet_id,
                "startPageToken": start_page_token,
            }, config_file)
    return were_changes_in_a_file


def get_gheets_value(spreadsheet_id):
    """
    Возвращает таблицу Gsheets
    """
    values = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range='A1:E1000',
        majorDimension='ROWS'  # ROWS COLUMNS
    ).execute()
    pprint(values.get('values'))
    return values.get('values')


if __name__ == '__main__':
    while True:
        """
        Каждую минуту проверяем были ли изменения, если были то пересоздаем таблицу
        """
        if check_changes():
            gheets_value = get_gheets_value(spreadsheet_id)

            dollar_data = requests.get('https://www.cbr-xml-daily.ru/daily_json.js').json()
            dollar_price = dollar_data['Valute']['USD']['Value']

            with db:
                GoogleSheeds.delete()
                for value in gheets_value:
                    if value == ['№', 'заказ №', 'стоимость,$', 'срок поставки']:
                        pass
                    else:
                        GoogleSheeds.create(
                            # order_id=value[0],
                            order_name=value[1],
                            price_dollar=value[2],
                            date=value[3],
                            price_rubles=int(value[2]) * dollar_price
                        )
