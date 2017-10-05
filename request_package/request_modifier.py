import re

from request_package.request_object import RequestObject


class RequestModifier:
    def __init__(self, marked_request, payloads, config):
        """ Конструктор

        :param marked_request: строка с промаркированным запросом
        :param payloads: список пейлоадов
        :param config: конфигурационный файл
        """
        self.QUERY_STRING = 1
        self.HEADERS = 2
        self.DATA = 4

        self.marked_request = RequestObject(marked_request)
        self.payloads = payloads
        self.config = config

        self.injection_mark = self.config['Program']['injection_mark']
        self.modified_requests = []

    def get_modified_requests(self, flags=7):
        """ Возвращает список измененных запросов

        Модифицирует части начального запроса согласно параметру flags. Для модификации строки запроса используется
        QUERY_STRING (число 1), для модификации заголовков - HEADERS (число 2), для данных - DATA (число 4). Для комби-
        нации модификаций используй сумму соответствующих констант.

        :param flags: Число, указывающее, какие части запроса модифицировать
        :return: Список request_object'ов с измененными параметрами
        """
        # модифицируем строку запроса и собираем остальную часть
        # модифицируем хидеры и собираем остальные части
        # модифицируем data и собираем остальные части
        if flags & self.QUERY_STRING:
            self._modify_query_string()
        if flags & self.HEADERS:
            self._modify_headers()
        if flags & self.DATA:
            self._modify_data()

        return self.modified_requests

    def _modify_query_string(self):
        pattern = '([^?&]+)=({mark}{mark}|{mark}.+?{mark})|({mark}(.+?){mark})'.format(mark=self.injection_mark)
        re.sub(pattern, self._feed_query_string, self.marked_request.query_string)

    def _feed_query_string(self, match):
        # Если строка запроса формата /path/to/file?param1=value1
        is_rest = False
        if match.regs[2] != (-1,-1):
            start, end = match.regs[2]
            param_name = match.string[match.regs[1][0]:match.regs[1][1]]
        # иначе REST
        else:
            is_rest = True
            start, end = match.regs[4]
            param_name = 'Query string'

        for payload in self.payloads:
            modified_value = (match.string[start:end] + payload).replace(self.injection_mark, '')
            modified_query_string = match.string[:start] + modified_value + match.string[end:]
            modified_raw_request = '\r\n'.join([modified_query_string] + self.marked_request.headers_list) \
                                   + '\r\n\r\n' + self.marked_request.data
            modified_raw_request = modified_raw_request.replace(self.injection_mark, '')

            kwargs = {
                'testing_param': param_name,
                'test_info': param_name + '=' + modified_value if not is_rest else param_name + ': ' + modified_value,
                'payload': payload
            }

            self.modified_requests.append(
                RequestObject(modified_raw_request, **kwargs))

    def _modify_headers(self):
        marked_values_regexp = '{mark}.+?{mark}'.format(mark=self.injection_mark)

        for ind, header in enumerate(self.marked_request.headers_list):
            marked_values = list(re.finditer(marked_values_regexp, header))

            if marked_values:
                for match in marked_values:
                    start, end = match.regs[0]

                    for payload in self.payloads:
                        modified_value = (match.string[start:end] + payload).replace(self.injection_mark, '')
                        testing_param = modified_value.split('=')[0] if '=' in modified_value else ''
                        modified_header = header[:start] + modified_value + header[end:]
                        modified_headers = self.marked_request.headers_list[:ind] + [modified_header] \
                                           + self.marked_request.headers_list[ind + 1:]
                        modified_raw_request = '\r\n'.join([self.marked_request.query_string] + modified_headers) \
                                               + '\r\n\r\n' + self.marked_request.data
                        modified_raw_request = modified_raw_request.replace(self.injection_mark, '')

                        kwargs = {
                            'testing_param': testing_param,
                            'test_info': '{}: {}'.format(header.split(': ')[0], modified_value),
                            'payload': payload
                        }

                        self.modified_requests.append(RequestObject(modified_raw_request, **kwargs))

    def _modify_data(self):
        if self.marked_request.content_type == 'plain':
            pattern = '([^?&]+)=({mark}{mark}|{mark}.+?{mark})'.format(mark=self.injection_mark)
            func = self._feed_plain_data
        elif self.marked_request.content_type == 'json':
            pattern = '{mark}.+?{mark}'.format(mark=self.injection_mark)
            func = self._feed_json_data
        # TODO: обсудить мораторий на использование request_modifier в xml запросах
        elif self.marked_request.content_type == 'xml':
            return None
            pattern = '{mark}.+?{mark}'.format(mark=self.injection_mark)
            func = self._feed_xml_data
        else:
            raise Exception('Exception in _modify_data request_modifier.py')

        re.sub(pattern, func, self.marked_request.data)

    def _feed_plain_data(self, match):
        start, end = match.regs[2]
        param_name = match.string[match.regs[1][0]:match.regs[1][1]]

        for payload in self.payloads:
            modified_value = (match.string[start:end] + payload).replace(self.injection_mark, '')
            modified_data = match.string[:start] + modified_value + match.string[end:]
            modified_raw_request = self.marked_request.query_string + '\r\n' + '\r\n'.join(
                self.marked_request.headers_list) \
                                   + '\r\n\r\n' + modified_data
            modified_raw_request = modified_raw_request.replace(self.injection_mark, '')

            kwargs = {
                'testing_param': param_name,
                'test_info': param_name + '=' + modified_value.replace(self.injection_mark, ''),
                'payload': payload
            }

            self.modified_requests.append(RequestObject(modified_raw_request, **kwargs))

    def _feed_json_data(self, match):
        start, end = match.regs[0]
        for payload in self.payloads:
            _start, _end = self._get_testing_json_param_pos(match, len(payload))
            modified_value = match.string[start:end] + payload
            modified_data = match.string[:start] + modified_value + match.string[end:]

            test_info = modified_data[_start:_end].replace(self.injection_mark, '')

            modified_raw_request = '\r\n'.join([self.marked_request.query_string] + self.marked_request.headers_list) \
                                   + '\r\n\r\n' + modified_data
            modified_raw_request = modified_raw_request.replace(self.injection_mark, '')

            kwargs = {
                'testing_param': test_info.split(':')[0],
                'test_info': modified_data[_start:_end].replace(self.injection_mark, ''),
                'payload': payload
            }

            self.modified_requests.append(RequestObject(modified_raw_request, **kwargs))

    # инжект внутрь ![CDATA[INJ]]
    def _feed_xml_data(self, match):
        start, end = match.regs[0]
        for payload in self.payloads:
            _start, _end = self._get_testing_xml_param_pos(match, len(payload))
            modified_value = match.string[start:end] + payload
            modified_data = match.string[:start] + modified_value + match.string[end:]
            test_info = modified_data[_start:_end].replace(self.injection_mark, '')
            modified_raw_request = '\r\n'.join([self.marked_request.query_string] + self.marked_request.headers_list) \
                                   + '\r\n\r\n' + modified_data
            modified_raw_request = modified_raw_request.replace(self.injection_mark, '')

            kwargs = {
                'testing_param': test_info.split('=')[0] if '=' in test_info else '',
                'test_info': test_info,
                'payload': payload
            }

            self.modified_requests.append(RequestObject(modified_raw_request, **kwargs))

    def _get_testing_json_param_pos(self, match, payload_len):
        start, end = match.regs[0]
        brackets = 0
        while True:
            start -= 1
            if match.string[start] == ':':
                break
            elif match.string[start] == '[':
                brackets += 1
        if match.string[start - 1] == '"':
            start -= 2
            while True:
                if match.string[start] == '"' and match.string[start - 1] != '\\':
                    break
                start -= 1
        else:
            start -= 2
            while match.string[start] not in [' ', '{']:
                start -= 1
        while brackets > 0:
            if match.string[end] == ']':
                brackets -= 1
            elif match.string[end] == '[':
                brackets += 1
            end += 1
        end += 1 if match.string[end] == '"' else 0
        return start, end + payload_len

    def _get_testing_xml_param_pos(self, match, payload_len):
        start, end = match.regs[0]
        if match.string[start - 1] == '>':
            start -= 2
            while True:
                if match.string[start] == '<':
                    break
                start -= 1
            end += 1
            while True:
                if match.string[end] == '>' and match.string[end - 1] != '\\':
                    end += 1
                    break
                end += 1
        else:
            start -= 1
            while True:
                if match.string[start] in ['\r', '\n', '\t', '\f', ' ']:
                    start += 1
                    break
                start -= 1
            end += 1
            while True:
                if match.string[end] in ['\r', '\n', '\t', '\f', ' ', '>']:
                    break
                end += 1
        return start, end + payload_len
