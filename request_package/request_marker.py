import json
import re

from request_package.json_mark import MyJSONEncoder


# TODO: Маркировать точечно (page=abFUZZcd.html вместо page=abFUZZFUZZcd.html)
class RequestMarker:
    # TODO: Разобраться с X-Forwarded-For: 127.0.0.1, 127.0.0.1
    # TODO: пропускать уже помеченные параметры
    def __init__(self, request_object, properties):
        """Создает экзепляр класса RequestAnalyzer

        :param request_object: RequestObject экземпляр
        :param properties: словарь, содержащий конфгурацию программы
        """
        self.properties = properties
        self.injection_mark = '{mark}{0}{mark}'.format('{}', mark=self.properties['Program']['injection_mark'])

        self.excluded_headers = {'Host', 'Accept', 'Accept-Language', 'Accept-Encoding', 'Connection', 'Content-Type',
                                 'Content-Length', 'Upgrade-Insecure-Requests', 'X-Originating-IP', 'X-Remote-IP',
                                 'X-Remote-Addr', 'X-Client-IP', 'X-Forwarded-Host', 'X-Remote-IP'} # Если можно будет указывать, какие параметры пропускать
        self.all_headers = set()  # Все имена распарсенных хидеров будут здесь
        # Хидеры, которые будут добавлены в запрос, если их в нем нет
        self.extra_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; U; Android 4.0.3; ko-kr; LG-L160L Build/IML74K) AppleWebkit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30',
            'Referer': '127.0.0.1',
            'X-Forwarded-For': '127.0.0.1',
            'X-Forwarded-Host': 'localhost',
            'X-Originating-IP': '127.0.0.1',
            'X-Remote-IP': '127.0.0.1',
            'X-Remote-Addr': '127.0.0.1',
            'X-Client-IP': '127.0.0.1'
        }

        self.request_object = request_object

        self._mark_request()

    def get_marked_request(self):
        return self.request_object.market_request

    def get_initial_request(self):
        return self.request_object.raw_request

    def _mark_request(self):
        """Помечает отдельные участки запроса и собирает их вместе в self.request_object.marked_raw_request"""
        self._mark_query_string()
        self._mark_headers()
        self._mark_data()

        self.request_object.market_request = '\r\n'.join([self.request_object.query_string] + self.request_object.headers_list)\
                                             + '\r\n\r\n' + self.request_object.data

    def _mark_query_string(self):
        """Помечает значения в строке запроса"""
        method, uri, http_ver = self.request_object.query_string.split(' ')

        if '?' in uri:
            uri = self._mark_by_regexp(uri, '=([^&]+)')
            uri = self._mark_empty_params(uri)
        # REST style
        else:
            uri = self._mark_by_regexp(uri, '(?<=/)(.+?)(?=/)')

        self.request_object.query_string = ' '.join([method, uri, http_ver])

    def _mark_headers(self):
        """Помечает значения в хидерах"""
        modified_headers = []

        for header in self.request_object.headers_list:
            try:
                name, value = header.split(': ')
                self.all_headers.add(name)

                if name not in self.excluded_headers:
                    # Эвристика
                    if (' ' not in value) or (';' not in value and '=' not in value) \
                            or (';' in value and '=' not in value):
                        value = self.injection_mark.format(value)
                    else:
                        value = self._mark_by_regexp(value, '([\S]+?=[^\s;]+)')

                modified_headers.append(': '.join([name, value]))

            except ValueError as ve:
                print('[!] Exception in _mark_headers. Message: {}'.format(ve))

        for header, value in self.extra_headers.items():
            if header not in self.all_headers:
                modified_headers.append(': '.join([header, self.injection_mark.format(value)]))

        self.request_object.headers_list = modified_headers

    def _mark_data(self):
        """Помечает параметры в данных"""
        if not self.request_object.data:
            return

        content_type = self.request_object.content_type

        if content_type == 'plain':
            self._mark_data_plain()
        elif content_type == 'json':
            self._mark_data_json()
        elif content_type == 'xml':
            self._mark_data_xml()
        else:
            pass

    def _mark_data_plain(self):
        """Помечаются данные вида param1=value1&param2=value2"""
        self.request_object.data = self._mark_by_regexp(self.request_object.data, '=([^&]+)')
        self.request_object.data = self._mark_empty_params(self.request_object.data)

    def _mark_data_json(self):
        """Помечаются данные, представленные json"""
        json_encoder = MyJSONEncoder(self.injection_mark)
        data = self.request_object.data

        data = json.loads(data)
        self.request_object.data = json_encoder.encode(data)

    def _mark_data_xml(self):
        """Помечаются данные, представленные xml"""
        attr_regexp = '''(?<!version)(?<!encoding)=['"](.+?)['"]'''
        item_regexp = '''<[^\/]+?>([^\<\>]+?)<\/.+?>'''
        data = self.request_object.data

        data = self._mark_by_regexp(data, attr_regexp, group=1)
        data = self._mark_by_regexp(data, item_regexp)
        self.request_object.data = data

    def _mark_by_regexp(self, string, regexp, prefix='', group=1, flags=0):
        """Помечает параметры в строке по regexp'у

        :param string: Строка, в которой помечаются параметры
        :param regexp: Регулярное выражение, по которому они ищутся
        :param prefix: Префикс строки, на которую заменяется найденная группа
        :return: Измененная строка string
        """
        string = re.sub(regexp,
                        lambda x: prefix + x.group(0).replace(x.group(group),
                                                              self.injection_mark.format(x.group(group))),
                        string, flags=flags)
        return string

    def _mark_empty_params(self, string):
        """Помечает пустые параметры

        :param string: Строка, в которой пустые параметры ищутся
        :return: Измененная строка string
        """
        return re.sub('=(&|$)', lambda x: '=' + self.injection_mark.format('') + ('&' if '&' in x.group() else ''),
                      string)
