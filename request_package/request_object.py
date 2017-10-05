import re


class RequestObject:
    def __init__(self, request, testing_param='', payload='', test_info=''):
        self.gid = None
        self.id = None

        self.testing_param = testing_param
        self.test_info = test_info
        self.payload = payload

        self.raw_request = request
        self.raw_response = ''
        self.market_request = ''

        self.query_string = ''
        self.method = ''
        self.url_path = ''
        self.host = ''

        # хидеры должны быть в том же порядке, в котором пришли
        self.headers = dict()
        self.headers_list = []
        self.content_type = None
        self.charset = 'utf8'
        self.data = ''
        self.known_types = {'text': {'html': 'plain', 'plain': 'plain', 'xml': 'xml'},
                            'application': {'atom+xml': 'xml', 'json': 'json', 'soap+xml': 'xml', 'xhtml+xml': 'xml',
                                            'xml-dtd': 'xml', 'xop+xml': 'xml', 'xml': 'xml',
                                            'x-www-form-urlencoded': 'plain'}}

        self.normalize_raw_request()
        self._parse_request(self.raw_request)

    def _parse_request(self, raw_request):
        """ Распаковывает сырой запрос в объект"""
        # Разбиваем сырой запрос на 'строку запроса', 'хидеры' и 'дату'
        try:
            self.headers, self.data = raw_request.split('\r\n\r\n')
        except ValueError as ve:
            self.headers, self.data = raw_request, None

        self.query_string, *self.headers = self.headers.split('\r\n')
        self.method, self.url_path, *_ = self.query_string.split()

        # Httplib слетает по timeout'у, если в заголовке Host значение 127.0.0.1
        self.headers = ['Host: localhost' if x.startswith('Host') and '127.0.0.1' in x else x for x in self.headers ]

        # Удаляем хидер Content-Length
        self.headers = [x for x in self.headers if not x.startswith('Content-Length')]

        self.headers_list = self.headers[:]
        self.headers = dict([i.split(': ') for i in self.headers])
        self.host = self.headers['Host'].split(':',maxsplit=1)[0]

        self._identify_content_type()

    def _identify_content_type(self):
        """Находит хидер Content-type, парсит type и subtype и определяет по known_types форму данных"""
        # content_type = next((header for header in self.headers if header.startswith('Content-Type')), None)
        content_type = self.headers.get('Content-Type')
        content_type = re.search('([\w-]+/[\w-]+)', content_type) if content_type is not None else None

        if content_type:
            content_type = content_type.group(1)
            type, subtype = content_type.split('/')
            self.content_type = self.known_types.get(type)
            self.content_type = self.content_type.get(subtype) if self.content_type else None
        else:
            self.content_type = 'plain'

    def normalize_raw_request(self):
        "Приводит сырой запрос к стандарту"
        if not '\r\n' in self.raw_request:
            self.raw_request = self.raw_request.replace('\n', '\r\n')


if __name__ == '__main__':
    with open('test_requests/request.txt') as f:
        raw_request = f.read()

    ro = RequestObject(raw_request)
