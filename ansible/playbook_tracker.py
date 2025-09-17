#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from datetime import datetime
from sys import argv
import os
import re
from pprint import pprint
import sqlite3
import subprocess
import getpass


def check_files(argv):
    """
    Функция работает с аргументами, полученными из командной строки.
    Определяются имя директории для файлов плейбука и имя файла базы данных
    для отслеживания результатов выполнения плейбука на хостах. Возвращает
    словарь с этими переменными.
    """
    files = {}
    directory = argv[1].rstrip('.yaml')
    db = f"""{directory}/{directory}.db"""
    if not os.path.exists(directory):
        os.mkdir(directory)
    if not os.path.exists(db):
        connection = sqlite3.connect(db)
        connection.execute('''create table hosts
            (hostname text not NULL primary key,
            ok integer,
            changed integer,
            unreachable integer,
            failed integer,
            skipped integer,
            rescued integer,
            ignored integer)''')
        connection.close()
    files['dir'] = directory
    files['db'] = db
    return files


def inventory_data_read():
    """
    Функция сохраняет данные из файла инвентаризации в словарь вида
    'группа хостов': 'хост' и возвращает его.
    """
    host_group_regex = re.compile(r'\[(.+?)\]')
    with open('путь к inventory', 'r') as file:
        hosts_iter = iter(file)
        hosts_dict = {}
        for elem in hosts_iter:
            if host_group_regex.search(elem):
                group_name = host_group_regex.search(elem).group(1)
                hosts_dict[group_name] = []
            elif elem == '\n':
                pass
            else:
                hosts_dict[group_name].append(elem.strip())
        return hosts_dict


def data_compare(hosts_dict, files):
    """
    Функция сравнивает данные из словаря инвентаризации и базы данных
    плейбука (если она есть). Возвращает множество хостов, для которых в базе
    отсутствует статут успешного выполнения плейбука.
    """
    connection = sqlite3.connect(files['db'])
    cursor = connection.cursor()
    cursor.execute(
        "SELECT hostname FROM hosts WHERE unreachable = '0' AND failed = '0'")
    select = cursor.fetchall()  # список кортежей
    tmp = []
    for elem in select:
        tmp.append(elem[0])
    completed = set(tmp)
    inventory = set(hosts_dict['arm'])
    result = inventory - completed
    return result


def target_inventory_write(files, result):
    """
    Записывается новый файл инвентаризации (без хостов, успешно обработанных
    за предыдущие запуски прейбука).
    """
    with open(f"""{files['dir']}/new_inventory""", 'w') as f:
        f.write('[arm]\n')
        for elem in result:
            f.write(f"""{elem}\n""")


def playbook_run(files, argv):
    """
    Запуск ansible с новым файлом инвентаризации, вывод stdout записывается в
    файл с датой и временем запуска плейбука в имени. Функция возвращает имя
    этого лог-файла.
    """
    print("Введите пароль для авторизации по протоколу ssh:")
    password = getpass.getpass()
    cmd = [
        'sshpass',
        '-p', f"""{password}""",
        'ansible-playbook',
        '-e', f"""ansible_sudo_pass={password}""",
        '-e', f"""ansible_python_interpreter=/usr/bin/python3""",
        '-i', f"""{files['dir']}/new_inventory""",
        # '-vvvv',
        f"""{argv[1]}"""
    ]
    date = str(datetime.now())
    log_name = f"""{files['dir']}/{date}.log"""
    with open(log_name, 'w') as f:
        run = subprocess.run(cmd, stdout=subprocess.PIPE, encoding='utf-8')
        f.write(run.stdout)
    return log_name


def db_update(files, log_file):
    result_regexp = re.compile(r'PLAY RECAP.+$', re.DOTALL)
    problems_regexp = re.compile(
        r'^(?P<hostname>\S+).+?'
        r'(?:ok=(?P<ok>\d+)) +'
        r'(?:changed=(?P<changed>\d+)) +'
        r'(?:unreachable=(?P<unreachable>\d+)) +'
        r'(?:failed=(?P<failed>\d+)) +'
        r'(?:skipped=(?P<skipped>\d+)) +'
        r'(?:rescued=(?P<rescued>\d+)) +'
        r'(?:ignored=(?P<ignored>\d+)) +$'
    )
    summary = []
    with open(log_file) as f:
        log = f.read()
    result_log = result_regexp.search(log).group(0)
    result_log_list = result_log.split('\n')
    for elem in result_log_list:
        result_sum = problems_regexp.search(elem)
        if result_sum:
            summary.append(result_sum.group(
                'hostname', 'ok', 'changed', 'unreachable',
                'failed', 'skipped', 'rescued', 'ignored'))
            connection = sqlite3.connect(files['db'])
            with connection:
                query = "INSERT OR REPLACE into hosts VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
                connection.executemany(query, summary)


def main():
    files = check_files(argv)
    inventory = inventory_data_read()
    target_hosts = data_compare(inventory, files)
    target_inventory_write(files, target_hosts)
    log_file = playbook_run(files, argv)
    db_update(files, log_file)


if __name__ == '__main__':
    main()
