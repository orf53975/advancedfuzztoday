import random
import re
import string
import codecs
from queue import Queue

from request_package.request_marker import RequestMarker
from request_package.request_modifier import RequestModifier
from request_package.request_object import RequestObject
from request_package.requester import Requester


class Analyzer:
    def __init__(self, properties):
        self.CONTENT_LENGTH = 1
        self.ROW_COUNT = 2
        self.REQUEST_TIME = 4
        self.WORD_COUNT = 8

        self.properties = properties

        self.reflected_patterns = set()
        self._reflect_payload = ''
        self.time_delta = (None, None)

        self.initial_request = self.get_initial_request()
        self.marked_raw_request = RequestMarker(self.initial_request, self.properties).get_marked_request()

        self.response_queue = Queue()
        self.standard_response = self.get_standard_response()

        self.properties['Program']['standard_response'] = self.standard_response

    def get_modified_requests(self, payloads, flags=7):
        """ Возвращает список измененных запросов

        Модифицирует части начального запроса согласно параметру flags. Для модификации строки запроса используется
        QUERY_STRING (число 1), для модификации заголовков - HEADERS (число 2), для данных - DATA (число 4). Для комби-
        нации модификаций используй сумму соответствующих констант.

        :param payloads: Нагрузки, дополняющие помеченные параметры
        :param flags: Число, указывающее, какие части запроса модифицировать
        :return: Список объектов RequestObject
        """
        if not isinstance(payloads, list):
            payloads = list(payloads)

        request_modifier = RequestModifier(self.marked_raw_request, payloads, self.properties)
        return request_modifier.get_modified_requests(flags=flags)

    def get_modified_request_groups(self, payloads, encode_list, flags=7):
        """ Возвращает список групп запросов, составленных из payloads с разными кодировками encode_list

        Для каждого пейлоада применяет различные кодировки из encode_list и объединяет в одну группу

        :param payloads: list нагрузок
        :param encode_list: list функций-кодировщиков
        :param flags: Указывает, какие части запроса модифицировать
        :return: list, содержащий кортежи запросов из одной группы
        """
        modified_payload_groups = []
        for encode_func in encode_list:
            modified_payload_groups.append(map(encode_func, payloads))

        modified_request_groups = []
        for payload_group in modified_payload_groups:
            modified_request_groups.append(self.get_modified_requests(payload_group, flags=flags))

        for gid, request_group in enumerate(zip(*modified_request_groups)):
            for id, request in enumerate(request_group):
                request.gid = gid
                request.id = id

        return modified_request_groups

    def get_payloads(self, payload_path):
        """ Возвращает список нагрузок из директории payloads

        :param payload_path: путь до файла с нагрузками относительно дирестории payloads
        :return: Список нагрузок payloads
        """

        with open(self.properties['Program']['payload_path'] + payload_path.lstrip('\\/')) as f:
            payloads = f.read().split('\n')
        return payloads

    def get_initial_request(self):
        """ Возвращает инициализирующий запрос

        :return: Инициализирующий запрос RequestObject
        """
        with codecs.open(self.properties['Main']['file'], 'r', encoding='utf8') as f:
            initial_request = f.read()
        return RequestObject(initial_request)

    def get_standard_response(self):
        """ Возвращает стандартный ответ на стандартный заспрос из initial_request

        С помощью объекта Requester выполяет стандартный запрос и помещает ответ в объект ResponseObject. Помимо прочего
        инициализирует переменнуж self.time_delta. Является необходимой частью работы анализера.
        :return: Объект ResponseObject
        """
        print('[!] Получение стандартного ответа')
        # Предварительная отчистка запроса от маркеров
        init_request = RequestObject(self.initial_request.raw_request.replace(self.properties['Program']['injection_mark'], ''))

        requester = Requester(response_queue=self.response_queue, properties=self.properties)
        standard_response = requester.get_standard_response(init_request)
        self.time_delta = (standard_response.request_time, standard_response.request_time)
        return standard_response

    def is_interesting_behavior(self, response_obj, flags=15):
        """ Сравнивает ответ со стандартным ответом

        :param response_obj:
        :param flags: Число. 1 - учитывать длину контента, 2 - учитывать кол-во строк, 4 - учитывать время запроса, 8 - учитывать кол-во слов.
        :return:
        """

        if flags & self.CONTENT_LENGTH and response_obj.content_length != self.standard_response.content_length:
            return True
        if flags & self.ROW_COUNT and response_obj.row_count != self.standard_response.row_count:
            return True
        if flags & self.REQUEST_TIME and not abs(self.standard_response.request_time - response_obj.request_time) < 5:
            return True
        if flags & self.WORD_COUNT and response_obj.word_count != self.standard_response.word_count:
            return True
        return False

    def analyze(self):
        raise NotImplemented

    def detect_reflected_patterns(self):
        """ Определяет паттерны для рефлексирующих параметров в теле ответа

        Генерирует специальную нагрузку, которая вставляется в каждый промаркированный параметр стандартного запроса.
        Затем в телах ответов ищутся строки по паттерну .+?({reflected}).+?\n, тем самым определяя паттерны для
        рефлексирующих строк в ответах.

        Рефлексирующие паттерны кладутся во множество reflected_patterns с помощью метода self._feed_reflected_rows.
        Параллельно замеряется минимум и максимум времени запросов в переменную self.time_delta
        """
        resp_queue = Queue()

        self._reflect_payload = ''.join([random.choice(string.digits) for i in range(8)])
        requests = self.get_modified_requests([self._reflect_payload])

        requester = Requester(requests, resp_queue, self.properties)
        requester.run()

        print('[!] Сравниваем метрики')
        while requester.is_running() or not resp_queue.empty():
            resp = resp_queue.get()
            self.time_delta = (min(resp.request_time, self.time_delta[0]), max(resp.request_time, self.time_delta[1]))

            reflected = self._reflect_payload

            pattern = '.+?({reflected}).+?\n'.format(reflected=reflected)
            re.sub(pattern, self._feed_reflected_rows, resp.raw_response)

    def detect_waf_ids_ips(self):
        # Считать, что везде есть waf
        return True

    def clean_reflected_rows(self, response_obj):
        """ Удаляет рефлексирующие строки в response_obj по паттернам из self.reflected_patterns

        :param response_obj: Объект ответа, который необходимо отчистить от  рефлексирующих строк
        :return:
        """
        raw_response = response_obj.raw_response
        for reflect_pattern in self.reflected_patterns:
            try:
                raw_response = re.sub(reflect_pattern, self._cut_non_whitespace, raw_response)
                response_obj.rebuild(raw_response)
            except Exception as e:
                # print(reflect_pattern + '\n' + str(e))
                pass
        return response_obj

    def dump_response(self, filename, response_obj, encoding='utf8'):
        """ Записывает ответ в файл

        :param filename: Имя файла. В процессе приводится к валидному имени
        :param response_obj: Объект ответа.
        :param encoding: Кодировка, в которой нужно записать в файл
        :return:
        """

        filename = self._get_valid_filename(filename)
        filepath = self.properties['Program']['script_path'] + '/dumps/'

        with open(filepath + filename, 'wb') as f:
            f.write(response_obj.raw_response.encode(encoding=encoding))

    def _get_valid_filename(self, filename):
        filename = str(filename).strip().replace(' ', '_')
        return re.sub(r'(?u)[^-\w.]', '', filename)

    def _cut_non_whitespace(self, match):
        start, stop = match.regs[0]
        whitespace_end = start

        while match.string[whitespace_end] in string.whitespace:
            whitespace_end += 1

        return match.string[start:whitespace_end]

    def _feed_reflected_rows(self, match):
        start, _ = match.regs[0]
        stop, _ = match.regs[1]

        search_suffix = '.+?\n'
        reflect_pattern = self._escape_pattern(match.string[start:stop]) + search_suffix

        self.reflected_patterns |= {reflect_pattern}

    def _escape_pattern(self, pattern):
        pattern = pattern.replace('"', '\"')  # экранируем двойные кавычки
        pattern = pattern.replace('(', '\(').replace(')', '\)')  # экранируем скобки
        pattern = pattern.replace('[', '\[').replace(']', '\]')  # экранируем скобки
        pattern = pattern.replace('$', '\$')
        pattern = pattern.replace('^', '\^')
        pattern = pattern.replace('.', '\.').replace('+', '\+').replace('?', '\?')

        return pattern
