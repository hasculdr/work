#!/usr/bin/env python3

import os
import sys
import logging
from pprint import pprint
from pyzabbix import ZabbixAPI, ZabbixAPIException


token = os.environ.get('Z_TOKEN')
host_group_name = 'Cisco switches'
"""
stream = logging.StreamHandler(sys.stdout)
stream.setLevel(logging.DEBUG)
log = logging.getLogger('pyzabbix')
log.addHandler(stream)
log.setLevel(logging.DEBUG)
"""

def get_host_group_id(host_group_name: str, api_obj) -> str:
    """Запрос ID группы по её имени"""
    host_group_id_request = api_obj.hostgroup.get(
        filter={'name': host_group_name}
    )
    return host_group_id_request[0]['groupid']

def get_group_hosts_ids(host_group_name: str, api_obj) -> list:
    """Запрос ID всех хостов"""
    group_hosts_ids_request = api_obj.host.get(
        selectGroups=host_group_name,
        output=['hostid', 'host']
    )
    return group_hosts_ids_request

def get_host_intf_id(host_id: str, api_obj) -> list:
    """Запрос ID интерфейсов хоста"""
    host_intf_id_request = api_obj.hostinterface.get(
        output='extend',
        hostids=host_id,
    )
    return host_intf_id_request

def update_host_intf(intf_id: str, api_obj):
    update_host_intf_request = api_obj.hostinterface.update(
        interfaceid=intf_id,
        useip='1',
    )

def add_host(hostname: str, ip: str, api_obj):
    """Создание узла сети через API"""
    try:
        host_add_request = api_obj.host.create(
            host={hostname}, # имя узла сети
            name=hostname, # видимое имя
            inventory_mode=1, # автоматически
            groups='<id>', # id группы
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

    with ZabbixAPI('https://...') as api_obj:
        api_obj.session.verify = False
        api_obj.login(api_token=token)
        print("Connected to Zabbix API Version {}".format(api_obj.api_version()))

        host_group_id = get_host_group_id(host_group_name, api_obj)
        hosts = get_group_hosts_ids(host_group_name, api_obj)
        for elem in hosts:
            if elem['groups'] == [{'groupid': host_group_id}]:
                intf_id = get_host_intf_id(elem['hostid'], api_obj)
                for subelem in intf_id:
                    if subelem['type'] == '2': # только для snmp-интерфейсов
                        update_host_intf(subelem['interfaceid'], api_obj)
