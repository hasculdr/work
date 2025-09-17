#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from glob import glob
from pprint import pprint
import re



def get_files_list():
    sw_list = glob('./Tue/*.conf') # путь к бекапам конфигов cisco
    return sw_list


def config_parse(cfg):
    """
    Парсинг файла конфигурации. Блок с настройкой физических интерфейсов
    делится на список интерфейсов. Для каждого интерфейса проверяется режим
    работы, если access - то выполняется поиск влана. Возвращается словарь
    {'имя узла сети': [список вланов]}
    """
    hostname = r'hostname (.+)\n'
    interfaces = r'(interface.+?)\n!\ninterface Vlan'
    access_vlan = r'access vlan (\d+)'
    access_mode = r'mode access'

    with open(cfg, 'r') as f:
        config = f.read()

    name = re.search(hostname, config)
    interfaces = re.search(interfaces, config, re.DOTALL)
    if interfaces:
        interfaces_list = interfaces.group(1).split('\n!\n')

        vlan_list = []
        for intf in interfaces_list:
            if re.search(access_mode, intf):
                vlan = re.search(access_vlan, intf)
                if vlan:
                    vlan_num = int(vlan.group(1))
                else:
                    vlan_num = 1
                vlan_list.append(vlan_num)

        return {name.group(1): vlan_list}


def parse_all(cfgs_list):
    """
    Запускает функцию парсинга файла конфигурации для всех файлов
    в списке, возвращаемом функцией get_files_list. Возвращает список
    словарей вида [{'имя узла сети': [список вланов]},]
    """
    vlans_summary = []
    for cfg in cfgs_list:
        switch_access_vlans = config_parse(cfg)
        if switch_access_vlans:
            vlans_summary.append(switch_access_vlans)
    return vlans_summary


def vlans_count(switch_access_vlans):
    """
    Функция для счета access-вланов в одном файле конфига.
    Возвращает словарь со отсортированным значением-множеством 
    """
    hostname = list(switch_access_vlans.keys())[0]
    vlans = list(switch_access_vlans.values())[0]
    counted_vlans = [(vlan, vlans.count(vlan)) for vlan in vlans]
    return {hostname: sorted(set(counted_vlans))}


def count_all(vlans_summary):
    """
    Запускает функцию счета access-вланов для всех словарей в списке,
    возвращаемом функцией parse_all. Возвращает словарь вида
    {'имя узла сети': [(влан, количество повторений)],}
    """
    counted_vlans = {}
    for elem in vlans_summary:
        counter = vlans_count(elem)
        counted_vlans.update(counter)
    return counted_vlans


def empty_table(counted_vlans):
    """
    Составляется множество всех найденных access-вланов; возвращаются:
    строка-заголовок таблицы из отсортированных по-возрастанию вланов,
    разделенных запятыми; словарь с данными для строк таблицы,
    каждая строка - словарь вида {коммутатор: {влан: None}}
    """
    switches = [] # список коммутаторов
    vlans = [] # список всех вланов на всех коммутаторах
    table_strings = {}
 
    for dict_elem in counted_vlans:
        switches.append(dict_elem)
        value = counted_vlans[dict_elem] # список кортежей (влан, количество)

        for tuple_elem in value:
            # собираем вланы для строки-заголовка
            vlans.append(tuple_elem[0]) # [0] - индекс влана
    header_vlans = sorted(set(vlans))
    header = re.sub(r'[\{\}\[\]\s]', '', f"""Коммутатор,{header_vlans}\n""")
 
    for switch in switches:
        temp_dict_key = {}
        temp_subdict_value = {}
        for vlan in header_vlans:
            temp_subdict_value[vlan] = None
        temp_dict_key[switch] = temp_subdict_value
        table_strings[switch] = temp_subdict_value
    
    return header, table_strings


def result_table(empty_table, data):
    """
    Функция обновляет "пустые" значения "строк таблицы" (словарь из функции
    empty_table) значениями из функции count_all (словарь с данными для всех
    коммутаторов);
    меняем формат данных о вланах на коммутаторе:
    {коммутатор: [(влан, количество),*]} на
    {коммутатор: {влан: количество,*}}
    """
    temp_dict_key = {}
    for elem_dict in data: # для каждого словаря форматируем значение
        temp_subdict_value = {}
        value = data[elem_dict] # список кортежей (влан, кол-во)
        for elem_tuple in value:
            temp_subdict_value[elem_tuple[0]] = elem_tuple[1]
        temp_dict_key[elem_dict] = temp_subdict_value # словарь с данными для коммутаторов

    header = empty_table[0] # 0 - заголовок
    result = empty_table[1] # 1 - словарь со словарями

    for elem in temp_dict_key: # elem - ключ
        result[elem].update(temp_dict_key[elem])

    return header, result


def write(result):
    header, data = result # распаковка
    draft = f"""{header}\n"""
    for elem in data: # elem - ключ словаря, имя коммутатора
        draft += (f"""{elem},""")
        switch_counter = data[elem] # словарь - счетчик вланов для одного коммутаторе
        for elem in switch_counter:
            draft += (f"""{switch_counter[elem]},""")
        draft += ('\n')

    with open('report.csv', 'w') as f:
        report = re.sub(r'None', '', draft)
        f.write(report)

if __name__ == '__main__':
    files = get_files_list()
    vlans = parse_all(files)
    summary = count_all(vlans)
    table = empty_table(summary)
    dataset = result_table(table, summary)
    write(dataset)


