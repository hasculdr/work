#!/usr/bin/env python3

from sys import argv
from textfsm import TextFSM
from tabulate import tabulate
from netmiko import (ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException)

def brief(data):
    with open('cisco_intf_brief.fsmtemplate') as template:
       fsm_obj = TextFSM(template)
       result = fsm_obj.ParseText(data) # на выходе список списков
    for elem in result:
        if elem[-1] == '': # костыль для выравнивания последней колонки
            elem[-1] = '0'
        if elem[1] == 'administratively down': # укорачиваем описания выключенных портов
            elem[1] = '*down'
        # перевод трафика в килобиты/сек
        inrate = int(elem[6]) / 1024
        outrate = int(elem[7]) / 1024
        # конвертирование скорости интерфейса в удобный вид
        if int(elem[5]) % 1000000 == 0: # 1 Гбит/сек и выше 
            bw_val = int(elem[5]) // 1000000
            unit = 'Gb/s'
        elif int(elem[5]) % 100000 == 0: # 100 Мбит/сек
            bw_val = int(elem[5]) // 1000
            unit = 'Mb/s'
        else: # 10 Мбит/сек
            bw_val = int(elem[5]) // 1000
            unit = 'Mb/s'
        inperc_val = round(inrate * 100 / int(elem[5]), 2) # входящий трафик в процентах
        outperc_val = round(outrate * 100 / int(elem[5]), 2) # исходящий трафик в процентах
        bw = str(bw_val) + ' ' + unit
        inperc = str(inperc_val) + ' %'
        outperc = str(outperc_val) + ' %'
        # назначаем вычисленные значения вместо собранных с устройства
        elem[5] = bw
        elem[6] = inperc
        elem[7] = outperc
    return(tabulate(result, headers=fsm_obj.header, tablefmt='rst', numalign='right'))

def connect(device_dict):
    with ConnectHandler(**device_dict) as connection:
        data = connection.send_command('show interfaces')
        print(brief(data))

try: # попытка подключения по протоколу SSH
    device = {
        "device_type": "cisco_ios_ssh",
        "host": argv[1],
        "username": "<логин>",
        "password": "<пароль>",
        "secret": "cisco",
        "port": 22
        }
    connect(device)
except (NetmikoTimeoutException, NetmikoAuthenticationException) as err:
    pass