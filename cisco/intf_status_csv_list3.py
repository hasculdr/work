#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import getpass
from sys import argv
import re
import subprocess
from netmiko import (
    ConnectHandler,
    NetmikoAuthenticationException,
    NetmikoTimeoutException)


def user_input():
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


def dataset(argv):
    return argv[1:len(argv)]


def connect(auth_dict, dev):
    connection = False
    try:
        device_dict = {
            'device_type': 'cisco_ios_ssh',
            'host': dev,
            'username': auth_dict['radius_username'],
            'password': auth_dict['radius_password'],
            'secret': 'cisco',
            'port': 22,
        }
        connection = ConnectHandler(**device_dict)
    except NetmikoAuthenticationException:
        print("Неверные логин/пароль")
    except NetmikoTimeoutException:
        device_dict = {
            'device_type': 'cisco_ios_telnet',
            'host': dev,
            'username': auth_dict['local_username'],
            'password': auth_dict['local_password'],
            'secret': 'cisco',
            'port': 23,
        }
        connection = ConnectHandler(**device_dict)
    except NetmikoAuthenticationException:
        print("Неверные логин/пароль")
    finally:
        if connection:
            connection.enable()
            return connection
        else:
            raise Exception(
                "Не получилось подключиться к устройству")


def get_data(connection):
    output = connection.send_command('show interfaces status')
    hostname = connection.find_prompt().rstrip('#')
    return {'output':output, 'hostname':hostname}


def process_data(data_dict):
    regexp_intf = (
        r'(?P<intf>(?:(Fa)|(Gi))\d(?:/\d+)(?:/\d+)*)\s+'
        r'(?P<descr>.+?)'
        r'(?: +(connected)| +(notconnect)| +(disabled)| +(err-disabled))\s+'
        r'(?P<vlan>(\d+)|(trunk)).+')
    regexp_addr = r'Address: ((?:\d+\.){3}(?:\d+))'
    match = re.finditer(regexp_intf, data_dict['output'])
    result = ''
    for elem in match:
        if not elem.group('descr').startswith('-'):
            if '|' in elem.group('descr'):
                dnsname = elem.group('descr').split('|')[0]
            else:
                dnsname = elem.group('descr')
            nslookup = subprocess.run(
                ['nslookup', dnsname],
                stdout=subprocess.PIPE,
                encoding='utf-8')
            if nslookup.returncode == 0:
                ip = re.search(regexp_addr, nslookup.stdout).group(1)
                result += (
                    f"""{data_dict['hostname']},"""
                    f"""{elem.group('intf')},"""
                    f"""{elem.group('descr')},"""
                    f"""{elem.group('vlan')},{ip}\n""")
            else:
                result += (
                    f"""{data_dict['hostname']},"""
                    f"""{elem.group('intf')},"""
                    f"""{elem.group('descr')},"""
                    f"""{elem.group('vlan')}\n""")
        else:
            result += (
                f"""{data_dict['hostname']},"""
                f"""{elem.group('intf')},"""
                f"""{elem.group('descr')},"""
                f"""{elem.group('vlan')}\n""")
    return result


def write(report, devices):
    filename = 'report'
    #filename = '_'.join(devices)
    with open(f"""{filename}.csv""", 'w') as f:
    # with open('report.csv', 'w') as f:
        f.write(report)


def main():
    auth = user_input()
    devices = dataset(argv)
    report = ''
    for dev in devices:
        conn = connect(auth, dev)
        data = get_data(conn)
        conn.disconnect()
        result = process_data(data)
        report += result
        print(f"""{dev} проверен""")
    write(report, devices)
    print('Файл записан')


if __name__ == '__main__':
    main()
