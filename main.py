import argparse
import codecs
import configparser
import os
import sys
from collections import defaultdict
from urllib.parse import urlparse

from core.controller import Controller

# TODO: Чекать целостность конфига
# TODO: Добавить --exclude/--include параметры
# TODO: --max-rate пакетов
# TODO: задержка ответа
class Main:
    URL_NOT_FOUND_CODE = 1
    REQUEST_PATH_NOT_FOUND_CODE = 2
    WORDLIST_PATH_CMD_NOT_FOUND_CODE = 3
    WORDLIST_PATH_CFG_NOT_FOUND_CODE = 4
    WORDLIST_PATH_ALL_NOT_FOUND_CODE = 5
    CONFIG_FILE_NOT_FOUND = 6

    def run(self):
        self.print_banner()

        self.arguments = self.get_arguments()
        self.check_config_exist()
        self.config_path = self.arguments.config_file if self.arguments.config_file else self.config_path
        self.config = self.read_config(self.config_path)

        # Указываем параметры без консоли
        #self._test()
        self.check_arguments()

        self.merge_args_and_config()

        if self.arguments.update_config:
            self.save_current_config()

        # Заполняем объект properties для большей маневренности в плане хранимых значений
        for section in self.config.sections():
            for option in self.config[section]:
                self.properties[section][option] = self.config.get(section, option)

        self.controller = Controller(self.properties)

    def __init__(self):
        # Для импорта по пути относительно main.py

        self.parser = argparse.ArgumentParser()
        self.script_path = os.path.dirname(os.path.realpath(__file__))
        sys.path.append(self.script_path)
        self.config_path = 'config.ini'

        # Объект, содержащий аргументы командной строки
        self.arguments = None
        # Объект класса ConfigParser, содержит предварительные настройки программы
        self.config = None
        # Словарь, содержащий все важные параметры программы
        self.properties = defaultdict(lambda: defaultdict(None))
        # Объект класса Controller, содержащий логику программы
        self.controller = None

    # Потестить
    def get_arguments(self):
        main_group = self.parser.add_argument_group('Main')
        main_group.add_argument('-u', '--url', dest='url', help='Адрес приложения (https://example.com:83)')
        main_group.add_argument('-f', '--file', dest='file', help='Файл с запросом')
        main_group.add_argument('-w', '--wordlist', dest='wordlist', default='fuzzing/test.txt',
                                help='Путь до словаря (абсолютный, относительный, от директории payloads)')
        main_group.add_argument('-t', '--threads', dest='threads', type=int, default=5, help='Количество потоков')
        main_group.add_argument('--proxy', dest='proxy',
                                help='Адрес прокси-сервера (http://127.0.0.1:8080, socks5://127.0.0.1:9050, ...), none в случае сброса настройки в конфиге')

        config_group = self.parser.add_argument_group('Config')
        config_group.add_argument('--update', dest='update_config', action='store_true',
                                  help='Обновить конфигурационный файл (properties.ini по умолчанию). \
                  Используй --properties-file, если файл не расположен по стандартному пути')
        config_group.add_argument('--properties-file', dest='config_file', help='Путь до конфигурационного файла')

        return self.parser.parse_args()

    # Потестить
    def check_arguments(self):
        _args, _cfg = self.arguments, self.config

        # Указан ли url
        if not _args.url and not _cfg['Main']['url']:
            self._print_error_message('Не найден url адрес цели', self.URL_NOT_FOUND_CODE)
            exit()

        # Указан ли путь до запроса
        if _args.file and not os.path.isfile(_args.file) or not _args.file and not _cfg['Main']['file']:

            self._print_error_message('Укажите коррекнтый путь до запроса через --file или в конфигурационном файле',
                                      self.REQUEST_PATH_NOT_FOUND_CODE)
            exit()

        # Если словарь задан через параметр
        if _args.wordlist:
            if not os.path.isfile(_args.wordlist) and not os.path.isfile('payloads/' + _args.wordlist):
                self._print_error_message('Укажите коррекнтый путь до словаря через -w',
                                          self.WORDLIST_PATH_CMD_NOT_FOUND_CODE)
                exit()
        # Если есть запись в конфиге (должен хранится полный путь)
        elif _cfg['Main']['wordlist']:
            if not os.path.isfile(_cfg['Main']['wordlist']):
                self._print_error_message('Укажите коррекнтый путь до словаря через -w',
                                          self.WORDLIST_PATH_CFG_NOT_FOUND_CODE)
                exit()
        # Если нет упоминаний о словаре
        else:
            self._print_error_message('Укажите коррекнтый путь до словаря через -w',
                                      self.WORDLIST_PATH_ALL_NOT_FOUND_CODE)
            exit()

        del _args, _cfg

        return 0

    def _print_error_message(self, message, code):
        print('[-] {message}'.format(message=message))
        self.parser.print_help()
        return code

    def print_banner(self):
        try:
            with open('banner.txt') as f:
                print(f.read())
        except:
            pass

    # Потестить
    def merge_args_and_config(self):
        # Указываем путь до main.py
        self.config['Program']['script_path'] = self.script_path
        self.config['Program']['payload_path'] = self.script_path + '/payloads/'

        if self.arguments.url:
            self.config['Main']['url'] = self.arguments.url

            url = urlparse(self.arguments.url)
            url_scheme = url.scheme if url.scheme else 'http'
            url_port = url.port if url.port else ('80' if url_scheme == 'http' else '443')

            self.config['RequestInfo']['scheme'] = url_scheme
            self.config['RequestInfo']['port'] = str(url_port)

        if self.arguments.file:
            self.config['Main']['file'] = self.arguments.file
        if self.arguments.threads:
            self.config['Main']['threads'] = str(self.arguments.threads)

        # Указываем путь до словаря
        if self.arguments.wordlist:
            if os.path.isfile(self.arguments.wordlist):
                self.config['Main']['wordlist'] = self.arguments.wordlist
            elif os.path.isfile('payloads/' + self.arguments.wordlist):
                self.config['Main']['wordlist'] = self.script_path + '/payloads/' + self.arguments.wordlist
            else:
                raise Exception('Беда со словарем')

        # Парсим --proxy
        if self.arguments.proxy:
            if self.arguments.proxy.lower() == 'none':
                self.config['Proxy']['scheme'] = ''
                self.config['Proxy']['host'] = ''
                self.config['Proxy']['port'] = ''
            else:
                proxy = urlparse(self.arguments.proxy)
                proxy_scheme = proxy.scheme
                proxy_host = proxy.hostname
                proxy_port = str(proxy.port)

                # Распихиваем --proxy
                self.config['Proxy']['scheme'] = proxy_scheme
                self.config['Proxy']['host'] = proxy_host
                self.config['Proxy']['port'] = proxy_port

    # Потестить нестандартный путь
    def read_config(self, path=None):
        config = configparser.ConfigParser()
        # Добавить Try\Catch на корявый конфиг
        if not path:
            config.read_file(codecs.open(self.script_path + '/config.ini', 'r', encoding='utf8'))
        else:
            config.read_file(codecs.open(path, 'r', encoding='utf8'))
        return config

    def save_current_config(self):
        with codecs.open(self.config_path, 'w', encoding='utf8') as config_file:
            self.config.write(config_file)

    def create_config(self):
        config = configparser.ConfigParser()
        config.add_section('Main')
        config.set('Main', 'url', '')
        config.set('Main', 'threads', '')
        config.set('Main', 'file', '')
        config.set('Main', 'wordlist', '')

        config.add_section('RequestInfo')
        config.set('RequestInfo', 'scheme', '')
        config.set('RequestInfo', 'port', '')

        config.add_section('Program')
        config.set('Program', 'script_path', '')
        config.set('Program', 'payload_path', '')
        config.set('Program', 'injection_mark', 'FUZZ')

        config.add_section('Proxy')
        config.set('Proxy', 'scheme', '')
        config.set('Proxy', 'host', '')
        config.set('Proxy', 'port', '')

        with open('config.ini', 'w') as config_file:
            config.write(config_file)

    def check_config_exist(self):
        _args = self.arguments

        if _args.config_file and not os.path.isfile(_args.file):
            self._print_error_message('[-] Указанного конфигурационного файла по пути --config-file не существует',
                                      self.CONFIG_FILE_NOT_FOUND)
            exit()
        if not os.path.isfile('config.ini'):
            answer = input('[!] Не удалось найти конфигурационный файл config.ini, создать новый? [Y/n]: ')
            if not answer or answer.lower() == 'y':
                self.create_config()
            else:
                self._print_error_message('Невозможно запустить скрипт без конфигурационного файла',
                                          self.CONFIG_FILE_NOT_FOUND)
                exit()

        del _args

    def _test(self):
        self.arguments.url = 'http://webinar.rgups.ru:8000'
        self.arguments.file = 'request.txt'
        self.arguments.threads = 6
        self.arguments.wordlist = 'fuzzing/test.txt'
        self.arguments.proxy = 'http://127.0.0.1:8080'
        self.arguments.update_config = True


if __name__ == '__main__':
    main = Main()
    main.run()
