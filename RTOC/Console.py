# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals

import os
import sys
import io

try:
    from whaaaaat import style_from_dict, Token, prompt, print_json, default_style, Separator, Validator, ValidationError
except ImportError:
    print('"whaaaaat" is not installed. Please install with "pip3 install whaaaaat" to use the console')
    sys.exit(0)

from .RTLogger.RTLogger import RTLogger

style = style_from_dict({
    Token.Separator: '#6C6C6C',
    Token.QuestionMark: '#FF9D00 bold',
    Token.Selected: '#5F819D',
    Token.Pointer: '#FF9D00 bold',
    Token.Instruction: '',  # default
    Token.Answer: '#5F819D bold',
    Token.Question: '',
})


text_trap = io.StringIO()


def enablePrint():
    #print(text_trap.getvalue())
    sys.stdout = sys.__stdout__


def disablePrint():
    sys.stdout = text_trap


print('Welcome to RTOC Console!\n\n')
disablePrint()

def mainmenu():
    mainmenu = [
        {
            'type': 'list',
            'name': 'mainmenu',
            'message': 'Mainmenu',
            'choices': [
                'Change settings',
                'Set autostart devices',
                'Inspect devices',
                # 'Setup backup-intervall',
                'Quit'
            ]
        }
    ]
    main = prompt(mainmenu, style=style)
    return main['mainmenu']


def settingsMenu():
    main = ""
    while not main == 'Back':
        menu = [
            {
                'type': 'list',
                'name': 'menu',
                'message': 'Select a setting-topic',
                'choices': [
                    'General',
                    'Telegram',
                    'RTOC Web',
                    'TCP-Server',
                    'Backup',
                    'Back'
                ]
            }
        ]
        main = prompt(menu, style=style)
        main = main['menu']
        if main == 'Telegram':
            telegramSettingsMenu()
        elif main == 'RTOC Web':
            webSettingsMenu()
        elif main == 'TCP-Server':
            tcpSettingsMenu()
        elif main == 'Backup':
            backupSettingsMenu()
        elif main == 'General':
            generalSettingsMenu()
    return main

def telegramSettingsMenu():
    # "telegram_bot": False,
    # "telegram_name": "RTOC-Remote",
    # "telegram_token": "",
    # "telegram_eventlevel": 1,
    # "telegram_chat_ids": [],
    menu = [
    {
        'type': 'input',
        'name': 'telegram_name',
        'message': 'Enter a Telegram Bot-Name: ',
        'default': logger.config['telegram_name']
    },
    {
        'type': 'input',
        'name': 'telegram_token',
        'message': 'Enter a Telegram Bot-Token: ',
        'default': logger.config['telegram_token']
    },
    {
        'type': 'input',
        'name': 'telegram_eventlevel',
        'message': 'Enter the telegram notification-level [0-2]: ',
        'default': str(logger.config['telegram_eventlevel'])
    },
    {
        'type': 'confirm',
        'name': 'telegram_bot',
        'message': 'Enable Telegram Bot? ',
        'default': str(logger.config['telegram_bot'])
    },
    ]
    main = prompt(menu, style=style)
    logger.config['telegram_name'] = main['telegram_name']
    logger.config['telegram_token'] = main['telegram_token']
    logger.config['telegram_eventlevel'] = int(main['telegram_eventlevel'])
    logger.config['telegram_bot'] = bool(main['telegram_bot'])
    logger.save_config()


def webSettingsMenu():
    menu = [
    {
        'type': 'confirm',
        'name': 'rtoc_web',
        'message': 'Enable the RTOC-Webserver? ',
        'default': str(logger.config['rtoc_web'])
    },
    ]

    main = prompt(menu, style=style)
    logger.config['rtoc_web'] = bool(main['rtoc_web'])
    logger.save_config()

def tcpSettingsMenu():
    menu = [
    {
        'type': 'input',
        'name': 'tcpPort',
        'message': 'Enter a TCP-Port [5050]: ',
        'default': str(logger.config['tcpPort'])
    },
    {
        'type': 'password',
        'name': 'tcppassword',
        'message': 'Enter a TCP-Password (leave blank for unsecured TCP): ',
        'default': str(logger.config['tcppassword'])
    },
    {
        'type': 'confirm',
        'name': 'tcpserver',
        'message': 'Enable the TCP-Server? ',
        'default': str(logger.config['tcpserver'])
    },
    ]

    main = prompt(menu, style=style)
    logger.config['tcpserver'] = bool(main['tcpserver'])
    logger.config['tcpPort'] = int(main['tcpPort'])
    logger.config['tcppassword'] = str(main['tcppassword'])
    logger.save_config()

def backupSettingsMenu():
    menu = [
    {
        'type': 'input',
        'name': 'backupIntervall',
        'message': 'Enter a backupIntervall: ',
        'default': str(logger.config['backupIntervall'])
    },
    {
        'type': 'input',
        'name': 'backupFile',
        'message': 'Enter a filepath for backups: ',
        'default': str(logger.config['backupFile'])
    },
    ]

    main = prompt(menu, style=style)
    logger.config['backupIntervall'] = int(main['backupIntervall'])
    logger.config['backupFile'] = str(main['backupFile'])
    logger.save_config()

def generalSettingsMenu():
    menu = [
    {
        'type': 'input',
        'name': 'defaultRecordLength',
        'message': 'Enter a defaultRecordLength: ',
        'default': str(logger.config['defaultRecordLength'])
    },
    {
        'type': 'input',
        'name': 'language',
        'message': 'Set system language [en/de]: ',
        'default': str(logger.config['language'])
    },
    ]

    main = prompt(menu, style=style)
    logger.config['defaultRecordLength'] = int(main['defaultRecordLength'])
    logger.config['language'] = str(main['language'])
    logger.save_config()
    # "language": "en",
    # "defaultRecordLength": 500000,

def autostartMenu():
    devices = logger.devicenames.keys()
    autorun_devices = load_autorun_plugins()
    states = []
    for dev in devices:
        if dev in autorun_devices:
            states.append(True)
        else:
            states.append(False)

    dicts = []
    for idx, item in enumerate(devices):
        dicts.append({'name': item, 'checked': states[idx]})
    menu = [
        {
            'type': 'checkbox',
            'name': 'menu',
            'message': 'Select autostart devices',
            'choices': dicts
        }
    ]
    main = prompt(menu, style=style)
    print(main['menu'])
    save_autorun_plugins(main['menu'])
    return main['menu']


def inspectDevicesMenu():
    main = ""
    while not main == 'Back':
        devices = logger.devicenames.keys()
        states = []
        for dev in devices:
            states.append(logger.pluginStatus[dev])

        devicetexts = []
        for idx, dev in enumerate(devices):
            stat = states[idx]
            if stat:
                stat = ": Running"
            else:
                stat = ": Stopped"
            devicetexts.append(dev+stat)
        devicetexts.append('Back')
        menu = [
            {
                'type': 'list',
                'name': 'menu',
                'message': 'Select a device',
                'choices': devicetexts
            }
        ]
        main = prompt(menu, style=style)
        main = main['menu']
        if not main == 'Back':
            inspectDeviceMenu(main)
    return main


def inspectDeviceMenu(device):
    #main = ""
    # while not main == 'Back':
    #     options = ['Start device', '5 signals', 'Clear data','Back']
    #     menu = [
    #         {
    #             'type': 'list',
    #             'name': 'menu',
    #             'message': 'Select an option for '+device,
    #             'choices': options
    #         }
    #     ]
    #     main = prompt(menu, style=style)
    #     main = main['menu']
    #     if not main == 'Back':
    #         pass
    # return main
    name=device.split(': ')
    if name[1] == 'Running':
        text = 'Do you really want to stop this device?'
        stopMode = True
    else:
        text = 'Do you want to start this device?'
        stopMode = False
    menu = [
    {
        'type': 'confirm',
        'name': 'startDevice',
        'message': text,
    },
    ]

    main = prompt(menu, style=style)
    if main['startDevice']:
        if stopMode:
            logger.stopPlugin(name[0], remote=True)
        else:
            logger.startPlugin(name[0], callback=None, remote=True)


def load_autorun_plugins():
    userpath = os.path.expanduser('~/.RTOC/autorun_devices')
    if not os.path.exists(userpath):
        with open(userpath, 'w', encoding="UTF-8") as f:
            f.write('')
        return []
    else:
        plugins = []
        try:
            with open(userpath, 'r', encoding="UTF-8") as f:
                content = f.readlines()
            # you may also want to remove whitespace characters like `\n` at the end of each line
            plugins = [x.strip() for x in content]
        except:
            print('error in '+userpath)
        return plugins


def save_autorun_plugins(devices):
    userpath = os.path.expanduser('~/.RTOC/autorun_devices')
    with open(userpath, 'w', encoding="UTF-8") as f:
        for dev in devices:
            f.write(dev+'\n')


logger = RTLogger(False)
ans = ''
try:
    while not ans == 'Quit':
        ans = mainmenu()
        if ans == 'Change settings':
            ans = settingsMenu()
        elif ans == 'Set autostart devices':
            autostartMenu()
        elif ans == 'Inspect devices':
            ans = inspectDevicesMenu()
except KeyboardInterrupt:
    print('Terminated by user')
finally:
    logger.stop()
