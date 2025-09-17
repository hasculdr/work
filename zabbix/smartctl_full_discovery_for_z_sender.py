#!/usr/bin/env python3

import re
import subprocess

info_sum_reg = re.compile(r'===.+?\n(.+?)\n\n', re.DOTALL)
info_reg = re.compile(r'(?P<vendor>^Model Family.+)*'
                    r'(?P<model>.+Model.+)*'
                    r'(?P<serial>^Serial.+)*'
                    r'(?P<firmware>^Firmware.+)*'
                    r'(?P<capacity>.*Capacity.+)*'
                    r'(?P<sector>Sector.+)*'
                    r'(?P<ata>^ATA.+)*'
                    r'(?P<sata>^SATA.+)*'
                    r'(?P<rotation>Rotation.+)*')

health_reg = re.compile(r'SMART overall.+?:\s(\S+?)\n')

attr_sum_reg = re.compile(r'ID#.+?\n\s+?\|', re.DOTALL)
attr_reg = re.compile(r'(?P<id>\d+)\s+' # идентификатор смарт-атрибута
                      r'(?P<attrname>\S+)\s+' # имя смарт-атрибута
                      r'(?P<flags>\S+)\s+' # флаг
                      r'(?P<value>\d+)\s+' # текущее значение
                      r'(?P<worst>\d+)\s+' # худшее значение
                      r'(?P<thresh>\d+)\s+' # значение, при достижении которого диск рекумендуется заменить
                      r'\S+\s+' # fail
                      r'(?P<raw>\d+).*') # raw value

disk_sum_temps = re.compile(r'\n\nSCT Status.+?\n\n.+?\n\n', re.DOTALL) # кусок вывода с температурами устройства
disk_cur_temp = re.compile(r'Current Temperature:\s+(\d+)') # рекомендуемый температурный режим
disk_warn_temps = re.compile(r'Min/Max recommended Temperature:\s+(\d+/\d+)') # рекомендуемый температурный режим
disk_crit_temps = re.compile(r'Min/Max Temperature Limit:\s+(\d+/\d+)') # аварийный температурный режим

def disks_discovery(): # функция обнаружения дисков в системе
    return_list = list()
    disks = subprocess.run(['/usr/sbin/smartctl', '--scan'], stdout=subprocess.PIPE)
    """
    пример вывода:
    $ /usr/sbin/smartctl --scan
    /dev/sda -d scsi # /dev/sda, SCSI device
    на случай более одного диска из вывода результата сканирования удаляется пустая строка,
    сам результат построчно сохраняется в список:
    """
    splited_output = disks.stdout.decode('utf-8').strip().split('\n')
    for string in splited_output: # string - строка с дисковым устройством, например, /dev/sda -d scsi # /dev/sda, SCSI device
        output_subelems = string.split() # такая строка делится по пробелам, результат сохраняется в списке
        dev_path = output_subelems[0] # первый элемент - имя файла устройства
        dev_file = re.search(r'/dev/(\w+)', dev_path)
        return_list.append(dev_file.group(1))
    return(return_list)

def disk_smart_info(smartctl_output, devname): # функция обнаружения инвентарных данных диска
    output = str()
    if info_sum_reg.search(smartctl_output):
        info = dict()
        for string in info_sum_reg.search(smartctl_output).group(1).split('\n'):
            if info_reg.search(string).group(0):
                match = info_reg.search(string).group(0) # строка целиком (например, 'Firmware Version: 01.01A01')
                key_value_list = match.split(':') # делим её по символу двоеточия
                info.update({key_value_list[0]: key_value_list[1]}) # каждая разделенная строка добавляется в словарь
    items = list(info.items())
    for elem in items: # в списке кортежи из двух элементов - заголовок и значение
        bad_key = elem[0] # соответствует ключу, но содержит пробелы 
        splited_key = bad_key.split(' ')
        good_key = splited_key[0] + splited_key[1] # пробелы удалены
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '\
                    "{#INFO}":' + '"{}"'.format(good_key) + '},'
    return(output)

def disk_smart_test(smartctl_output, devname):
    output = str()
    if health_reg.search(smartctl_output):
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#TEST}":"healthtest"}'
    return(output)

def disk_smart_temps(smartctl_output, devname):
    output = str()
    if disk_sum_temps.search(smartctl_output):
        temps = disk_sum_temps.search(smartctl_output).group(0) # кусок вывода с температурами устройства
    if disk_cur_temp.search(temps):
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#DESCR}":"Current temperature", "{#KEY}":"cur"},'
    if disk_warn_temps.search(temps):
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#DESCR}":"Min recommended temperature", "{#KEY}":"warn.min"},'
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#DESCR}":"Max recommended temperature", "{#KEY}":"warn.max"},'
    if disk_crit_temps.search(temps):
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#DESCR}":"Min temperature limit", "{#KEY}":"crit.min"},'
        output += '{"{#DEV}":' + '"{}", '.format(devname) + '"{#DESCR}":"Max temperature limit", "{#KEY}":"crit.max"},'
    return(output)

def disk_smart_attr(smartctl_output, devname):
    output = str()
    if attr_sum_reg.search(smartctl_output):
        """
        если регулярка возвращает строку,
        удаляем с конца символы переноса строки,
        результат делим по оставшимся символам переноса строки,
        сохраняем полученный список
        """
        attr_list = attr_sum_reg.search(smartctl_output).group(0).strip().split('\n')
        attr_list.pop(0) # удаляем строку-заголовок
        attr_list.pop(-1) # удаляем строку с началом описания флагов
        for elem in attr_list: # для каждой строки с атрибутом
            attr_string = attr_reg.search(elem) # используем регулярку с группировкой совпадений
            attr_id = attr_reg.search(elem).group('id') # id атрибута
            attr_name = attr_reg.search(elem).group('attrname') # имя атрибута
            attr_flags = attr_reg.search(elem).group('flags') # флаги атрибута
            output += '{"{#DEV}":' + '"{}", '.format(devname) + '\
                        "{#ATTRID}":' + '"{}", '.format(attr_id) + '\
                        "{#ATTRNAME}":' + '"{}", '.format(attr_name) + '\
                        "{#ATTRFLAGS}":' + '"{}"'.format(attr_flags) + '},'
    return(output)

hostname = (subprocess.run(('hostname'), stdout=subprocess.PIPE)).stdout.decode('utf-8').strip() # имя узла сети
disks_list = disks_discovery()
for disk in disks_list:
    """
    для каждого диска выполняется обнаружение данных S.M.A.R.T.,
    вывод команды регулярками делится на части,
    нужные данные оттуда собираются в строку, имитирующую формат zabbix_sender:
    каждая строка файла должна содержать разделенные пробелами: <имяузласети> <ключ> <значение>,
    где "именем_узла_сети" является имя наблюдаемого узла сети, как указано в веб-интерфейсе Zabbix,
    "ключем" является целевой ключ элемента данных и "значение" - отправляемое значение
    """
    smart = subprocess.run(['/usr/sbin/smartctl', '-x', '/dev/{}'.format(disk)], stdout=subprocess.PIPE) # полный вывод для диска
    smart_decoded = smart.stdout.decode('utf-8')
    disk_info = disk_smart_info(smart_decoded, disk) # сохраняем первую запись данных (инвентарные данные и некоторые характеристики устройства)
    json_info = ('[{}]'.format(disk_info)).replace(',]', ']')
    print('{} smartctl.info.discovery {}'.format(hostname, json_info))
    disk_test = disk_smart_test(smart_decoded, disk) # сохраняем вторую запись данных (тест состояния устройства)
    json_test = ('[{}]'.format(disk_test))
    print('{} smartctl.test.discovery {}'.format(hostname, json_test))
    disk_smart_temps = disk_smart_temps(smart_decoded, disk) # сохраняем третью запись данных (пограничные температурные значения устройства)
    json_smart_temps = ('[{}]'.format(disk_smart_temps)).replace(',]', ']')
    print('{} smartctl.temps.discovery {}'.format(hostname, json_smart_temps))
    disk_smart_attr = disk_smart_attr(smart_decoded, disk) # сохраняем четвертую запись данных (smart-атрибуты устройства)
    json_smart_attr = ('[{}]'.format(disk_smart_attr)).replace(',]', ']')
    print('{} smartctl.attr.discovery {}'.format(hostname, json_smart_attr))

