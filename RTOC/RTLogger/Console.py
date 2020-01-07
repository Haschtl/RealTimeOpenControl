# -*- coding: utf-8 -*-

from __future__ import print_function, unicode_literals

import os
import sys
import io
import traceback
import logging as log
log.basicConfig(level=log.INFO)
logging = log.getLogger(__name__)

try:
    # , print_json, default_style, Separator, Validator, ValidationError
    from whaaaaat import style_from_dict, Token, prompt
except ImportError:
    logging.error(
        '"whaaaaat" is not installed. Please install with "pip3 install whaaaaat" to use the console')
    sys.exit(1)

from .RTLogger import RTLogger

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
    # logging.info(text_trap.getvalue())
    sys.stdout = sys.__stdout__


def disablePrint():
    sys.stdout = text_trap


logging.info('Welcome to RTOC Console!\n\n')
disablePrint()


def mainmenu(logger):
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


def settingsMenu(logger):
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
                    'Websocket-Server',
                    'Backup',
                    'Back'
                ]
            }
        ]
        main = prompt(menu, style=style)
        main = main['menu']
        if main == 'Telegram':
            telegramSettingsMenu(logger)
        elif main == 'Websocket-Server':
            websocketSettingsMenu(logger)
        elif main == 'Backup':
            backupSettingsMenu(logger)
        elif main == 'General':
            generalSettingsMenu(logger)
    return main


def telegramSettingsMenu(logger):
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
            'default': logger.config['global']['name']
        },
        {
            'type': 'input',
            'name': 'telegram_token',
            'message': 'Enter a Telegram Bot-Token: ',
            'default': logger.config['telegram']['token']
        },
        # {
        #     'type': 'input',
        #     'name': 'telegram_eventlevel',
        #     'message': 'Enter the telegram notification-level [0-2]: ',
        #     'default': str(logger.config['telegram']['eventlevel'])
        # },
        {
            'type': 'confirm',
            'name': 'telegram_bot',
            'message': 'Enable Telegram Bot? ',
            'default': str(logger.config['telegram']['active'])
        },
    ]
    main = prompt(menu, style=style)
    logger.config['global']['name'] = main['telegram_name']
    logger.config['telegram']['token'] = main['telegram_token']
    # logger.config['telegram']['eventlevel'] = int(main['telegram_eventlevel'])
    logger.config['telegram']['active'] = bool(main['telegram_bot'])
    logger.save_config()


def websocketSettingsMenu(logger):
    menu = [
        {
            'type': 'input',
            'name': 'websocketPort',
            'message': 'Enter a Websocket-Port [5050]: ',
            'default': str(logger.config['websocket']['port'])
        },
        {
            'type': 'password',
            'name': 'websocketpassword',
            'message': 'Enter a Websocket-Password (leave blank for unsecured Websocket): ',
            'default': str(logger.config['websocket']['password'])
        },
        {
            'type': 'confirm',
            'name': 'websocketserver',
            'message': 'Enable the Websocket-Server? ',
            'default': str(logger.config['websocket']['active'])
        },
    ]

    main = prompt(menu, style=style)
    logger.config['websocket']['active'] = bool(main['websocketserver'])
    logger.config['websocket']['port'] = int(main['websocketPort'])
    logger.config['websocket']['password'] = str(main['websocketpassword'])
    logger.save_config()


def backupSettingsMenu(logger):
    menu = [
        {
            'type': 'input',
            'name': 'backupIntervall',
            'message': 'Enter a backupIntervall: ',
            'default': str(logger.config['backup']['intervall'])
        },
        {
            'type': 'input',
            'name': 'backupFile',
            'message': 'Enter a filepath for backups: ',
            'default': str(logger.config['backupFile'])
        },
    ]

    main = prompt(menu, style=style)
    logger.config['backup']['intervall'] = int(main['backupIntervall'])
    logger.config['backupFile'] = str(main['backupFile'])
    logger.save_config()


def generalSettingsMenu(logger):
    menu = [
        {
            'type': 'input',
            'name': 'defaultRecordLength',
            'message': 'Enter a defaultRecordLength: ',
            'default': str(logger.config['global']['recordLength'])
        },
        {
            'type': 'input',
            'name': 'language',
            'message': 'Set system language [en/de]: ',
            'default': str(logger.config['global']['language'])
        },
    ]

    main = prompt(menu, style=style)
    logger.config['global']['recordLength'] = int(main['defaultRecordLength'])
    logger.config['global']['language'] = str(main['language'])
    logger.save_config()
    # "language": "en",
    # "defaultRecordLength": 500000,


def autostartMenu(logger):
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
    logging.info(main['menu'])
    save_autorun_plugins(main['menu'])
    return main['menu']


def inspectDevicesMenu(logger):
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
            inspectDeviceMenu(main, logger)
    return main


def inspectDeviceMenu(device, logger):
    # main = ""
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
    name = device.split(': ')
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
        except Exception:
            logging.debug(traceback.format_exc())
            logging.error('error in '+userpath)
        return plugins


def save_autorun_plugins(devices):
    userpath = os.path.expanduser('~/.RTOC/autorun_devices')
    with open(userpath, 'w', encoding="UTF-8") as f:
        for dev in devices:
            f.write(dev+'\n')


def main():
    logger = RTLogger(False)
    ans = ''
    try:
        while not ans == 'Quit':
            ans = mainmenu(logger)
            if ans == 'Change settings':
                ans = settingsMenu(logger)
            elif ans == 'Set autostart devices':
                autostartMenu(logger)
            elif ans == 'Inspect devices':
                ans = inspectDevicesMenu(logger)
    except KeyboardInterrupt:
        logging.info('Terminated by user')
    finally:
        logger.stop()


if __name__ == '__main__':
    main()
