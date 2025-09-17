#!/usr/bin/env python3

import getpass
from pprint import pprint
import re
import subprocess
import socket
from netmiko import (
    ConnectHandler,
    ReadTimeout,
    NetmikoAuthenticationException,
    NetmikoTimeoutException,
)


def user_input() -> dict:
    print("Введите логин и пароль для централизованной авторизации:")
    rusername = input('Username: ')
    rpassword = getpass.getpass()
    print("Введите логин и пароль для локальной авторизации:")
    lusername = input('Username: ')
    lpassword = getpass.getpass()
    auth_dict = {
        'radius_username': rusername,
        'radius_password': rpassword,
        'local_username': lusername,
        'local_password': lpassword,
    }
    return auth_dict

def connect(auth_dict, dev):
    connection = False
    try:
        print(f"Подключаюсь по SSH к {dev}...")
        device_dict = {
            'device_type': 'cisco_ios_ssh',
            'host': dev,
            'username': auth_dict['radius_username'],
            'password': auth_dict['radius_password'],
            'secret': 'cisco',
            'port': 22,
        }
        connection = ConnectHandler(**device_dict)
        if connection:
            connection.enable()
            return connection
    except socket.timeout:
        print(f"Устройство {dev} недоступно или не существует")
    except NetmikoAuthenticationException:
        print(f"Неверные логин/пароль для {dev}")
    except NetmikoTimeoutException:
        print(f"Устройство {dev} недоступно по протоколу SSH") # отрабатывает дважды, второй раз как TimeoutError
    try:
        print(f"Подключаюсь TELNET'ом к {dev}...")
        device_dict = {
            'device_type': 'cisco_ios_telnet',
            'host': dev,
            'username': auth_dict['local_username'],
            'password': auth_dict['local_password'],
            'secret': 'cisco',
            'timeout': 3,
            'port': 23,
        }
        connection = ConnectHandler(**device_dict)
        if connection:
            connection.enable()
            return connection
    except NetmikoAuthenticationException:
        print(f"Неверные логин/пароль для {dev}")
    except socket.error:
        print(f"Устройство {dev} недоступно или не существует") # необходимо для NetmikoTimeoutException, при подключении по ssh по-умолчанию очень долгий таймаут

def send_commands_pack(connected_device):
    tmp_result = str()
    hostname = (connected_device.find_prompt())
    commands_cfg = [
        'ip ssh version 2',
    ]

    commands_show = [
        'show run | include ssh'
        'write memory',
    ]
    
    config = connected_device.send_config_set(commands_cfg, read_timeout=5)#, strip_prompt = False)
    tmp_result += hostname + '\n'
    for cmd in commands_show:
        try:
            show = connected_device.send_command(cmd)#, strip_prompt = False)
            tmp_result += show + '\n'
            print(show)
        except ReadTimeout:
            print("Таймаут получения ответа от устройства")
    return(tmp_result)

list_octet = list(range(2, 255))

result_output = '' # в эту строку записываем собранные с коммутаторов данные

if __name__ == "__main__":
    auth_dict = user_input()
    for num in list_octet:
        ip = f'10.x.y.{num}'
        connected_device = connect(auth_dict, ip)
        if connected_device:
            tmp = send_commands_pack(connected_device)
            result_output += tmp
            connected_device.disconnect
    print(result_output)
