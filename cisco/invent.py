#!/usr/bin/env python3

import getpass
import re

from scrapli import Scrapli
from scrapli import exceptions

print('Введите логин и пароль для централизованной авторизации:')
rlogin = input('Username: ')
print('Введите пароль')
rpassword = getpass.getpass()
print('Введите логин и пароль для локальной авторизации:')
llogin = input('Username: ')
print('Введите пароль')
lpassword = getpass.getpass()


result_output = '' # в эту строку записываем собранные с коммутаторов данные
error_output = '' # в эту строку записываем сообщения об ошибках scrapli
last_octet = range(2, 255) #диапазон ОТ и ДО, последнее число в диапазон не входит
for num in last_octet:
#начинаем попытку подключения с протокола SSH
    try:
        device = {
            "host": '10.x.y.{}'.format(num),
            "auth_username": rlogin,
            "auth_password": rpassword,
            "auth_secondary": "cisco",
            "auth_strict_key": False,
            "platform": "cisco_iosxe",
            "transport": "system",
            #"ssh_config_file": "~\.ssh\config", # костыль для отладки скрипта в gns
            "timeout_transport": 4
            }
        with Scrapli(**device) as ssh_connection:
            data = ssh_connection.send_command('show version | include Model number|System serial number|Base ethernet MAC Address|IOS', strip_prompt = False)
            dict_keys = ['ip', 'hostname', 'protocol', 'auth', 'model', 'serial', 'mac', 'ios', 'comment']
            info = dict.fromkeys(dict_keys, 'n/a')
            regexp = re.compile(r'(^.*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'(\S*)[>#].*')
            match = regexp.search(data.result)
            info['ip'] = device['host']
            info['hostname'] = match.group(5)
            info['protocol'] = 'ssh'
            info['auth'] = 'radius'
            info['model'] = match.group(3)
            info['serial'] = match.group(4)
            info['mac'] = match.group(2)
            info['ios'] = match.group(1)
            # добавляем в итоговую переменную данные, отформатированные с помощью f-строки и дополнительно символ перенова строки
            result_output += f'''{info['ip']};{info['hostname']};{info['protocol']};{info['auth']};{info['comment']};{info['model']};{info['serial']};{info['mac']};{info['ios']}''' + '\n'
            continue # если успешно - прекращаем попытки подключения для текущего узла сети
    except exceptions.ScrapliTimeout:
        print(f'''Устройство {device['host']} недоступно''')
        continue # прекращаем всякие действия для узла сети, не ответившего втечение тайм-аута
    except BaseException as error_obj:
        print(f'''{device['host']}: ошибка подключения по протоколу SSH:\n{str(error_obj)}''')
# вторая попытка - telnet с авторизацией через radius
    try:    
        device = {
            "host": '10.x.y.{}'.format(num),
            "auth_username": rlogin,
            "auth_password": rpassword,
            "auth_secondary": "cisco",
            "platform": "cisco_iosxe",
            "transport": "telnet",
            "port": 23,
            "timeout_transport": 2
            }
        with Scrapli(**device) as telnet_connection:
            data = telnet_connection.send_command('show version | include Model number|System serial number|Base ethernet MAC Address|IOS', strip_prompt = False)
            dict_keys = ['ip', 'hostname', 'protocol', 'auth', 'model', 'serial', 'mac', 'ios', 'comment']
            info = dict.fromkeys(dict_keys, 'n/a')
            regexp = re.compile(r'(^.*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'(\S*)[>#].*')
            match = regexp.search(data.result)
            info['ip'] = device['host']
            info['hostname'] = match.group(5)
            info['protocol'] = 'telnet'
            info['auth'] = 'radius'
            info['model'] = match.group(3)
            info['serial'] = match.group(4)
            info['mac'] = match.group(2)
            info['ios'] = match.group(1)
            # добавляем в итоговую переменную данные, отформатированные с помощью f-строки и дополнительно символ перенова строки
            result_output += f'''{info['ip']};{info['hostname']};{info['protocol']};{info['auth']};{info['comment']};{info['model']};{info['serial']};{info['mac']};{info['ios']}''' + '\n'
            continue # если успешно - прекращаем подключения для текущего узла сети
    except BaseException as error_obj:
        print(f'''{device['host']}: ошибка подключения по протоколу telnet (radius):\n{str(error_obj)}''')
# третья и последняя попытка подключения - telnet с локальными логином и паролем
    try:
        device = {
        "host": '10.x.y.{}'.format(num),
        "auth_username": llogin,
        "auth_password": lpassword,
        "auth_secondary": "cisco",
        "platform": "cisco_iosxe",
        "transport": "telnet",
        "port": 23,
        "timeout_transport": 2
        }
        with Scrapli(**device) as telnet_connection:
            data = telnet_connection.send_command('show version | include Model number|System serial number|Base ethernet MAC Address|IOS', strip_prompt = False)
            dict_keys = ['ip', 'hostname', 'protocol', 'auth', 'model', 'serial', 'mac', 'ios', 'comment']
            info = dict.fromkeys(dict_keys, 'n/a')
            regexp = re.compile(r'(^.*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'.*: (\S*)\n'
                        r'(\S*)[>#].*')
            match = regexp.search(data.result)
            info['ip'] = device['host']
            info['hostname'] = match.group(5)
            info['protocol'] = 'telnet'
            info['auth'] = 'local'
            info['model'] = match.group(3)
            info['serial'] = match.group(4)
            info['mac'] = match.group(2)
            info['ios'] = match.group(1)
            # добавляем в итоговую переменную данные, отформатированные с помощью f-строки и дополнительно символ перенова строки
            result_output += f'''{info['ip']};{info['hostname']};{info['protocol']};{info['auth']};{info['comment']};{info['model']};{info['serial']};{info['mac']};{info['ios']}''' + '\n'
    except BaseException as error_obj:
        print(f'''{device['host']}: ошибка подключения по протоколу telnet (локально):\n{str(error_obj)}''')
with open('inventory.csv', 'w') as file_object:
    file_object.write(result_output)