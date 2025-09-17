#!/usr/bin/env python3

import os
import sys
import logging
from pprint import pprint
from pyzabbix import ZabbixAPI, ZabbixAPIException


token = os.environ.get('Z_TOKEN')
"""
stream = logging.StreamHandler(sys.stdout)
stream.setLevel(logging.DEBUG)
log = logging.getLogger('pyzabbix')
log.addHandler(stream)
log.setLevel(logging.DEBUG)
"""

def read_input(filename: str) -> list:
    """Читаем указанный файл и возвращаем список строк"""
    with open(filename, 'r') as file_obj:
        return file_obj.readlines()

# def get_template_id(template_name: str, api_obj) -> str:
    # """Запрос ID шаблона по его имени"""
    # template_id_request = api_obj.template.get(
        # filter={'name': template_name}
    # )
    # return template_id_request[0]['templateid']

def add_host(hostname: str, ip: str, api_obj):
    """Создание узла сети через API"""
    try:
        host_add_request = api_obj.host.create(
            host={hostname}, # имя узла сети
            name=hostname, # видимое имя
            inventory_mode=1, # автоматически
            groups='id', # id группы
            interfaces=[{
                'type': '1', # агент
                'main': '1', # интерфейс по-умолчанию
                'useip': '0', # подключаться по dns-имени
                'ip': ip,
                'dns': hostname,
                'port': '10050',
                }],
            templates=[{'templateid': '<id шаблона>',}]
        )
        print(f"""Узел сети {hostname} добавлен""")
    except ZabbixAPIException as err:
        print(err)
        print(f""">>>>>Узел сети {hostname} не добавлен""")
        sys.exit()
 

if __name__ == "__main__":
    input_data = read_input('input') # список строк ip/dns обнаруженных серверов

    with ZabbixAPI('https://...') as api_obj:
        api_obj.session.verify = False
        api_obj.login(api_token=token)
        print("Connected to Zabbix API Version {}".format(api_obj.api_version()))

        for elem in input_data:
            split = elem.split(' ') # получаем список из 2-х элементов
            ip=split[1]
            hostname=split[1].strip('()')
            add_host(hstname, ip, api_obj)
