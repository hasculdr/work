#!/usr/bin/env python3

from sys import argv
import re
from netmiko import (ConnectHandler, NetmikoAuthenticationException)

device_dict = {
         "device_type": "cisco_ios_telnet",
         "host": argv[1],
         "username": "<логин>",
         "password": "<пароль>",
         "secret": "cisco",
         "port": 23,
         }

local_auth = {
             "username": "<логин>",
             "password": "<пароль>"
             }

reg_intf = r'((Fast|Gigabit)Ethernet\d/\d+(/\d+)*)'

def get_down_intf_list():
    result = list()
    connection.enable()
    response = connection.send_command('show interfaces | include line protocol is down')
    for elem in response.split():
        match = re.search(reg_intf, elem)
        if match:
            result.append(match.group(0))
    return(result)

def run_cable_diag(down_intf_list):
    for elem in down_intf_list:
       connection.send_command('test cable-diagnostics tdr interface {}'.format(elem))

def get_cable_diag_result(down_intf_list):
    result = list()
    for elem in down_intf:
        result.append(connection.send_command('show cable-diagnostics tdr interface {}'.format(elem)))
    return(result)

try:
    connection = ConnectHandler(**device_dict)
    down_intf = get_down_intf_list()
    run_cable_diag(down_intf)
    diag_result = get_cable_diag_result(down_intf)
    connection.disconnect()
    for elem in diag_result:
        print(elem)
except NetmikoAuthenticationException as err:
    device_dict.update(local_auth)
    connection = ConnectHandler(**device_dict)
    down_intf = get_down_intf_list()
    run_cable_diag(down_intf)
    diag_result = get_cable_diag_result(down_intf)
    connection.disconnect()
    for elem in diag_result:
        print(elem)
