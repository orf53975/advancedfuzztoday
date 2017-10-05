import re
from bs4 import BeautifulSoup


class ResponseObject:
    def __init__(self, raw_response=None, request_object=None, request_time=None, response_code=None,
                 response_headers=None):
        self.gid = request_object.gid
        self.id = request_object.id

        self.request_object = request_object
        self.raw_response = raw_response
        self.response_headers = response_headers

        self.test_info = self.request_object.test_info
        self.testing_param = self.request_object.testing_param
        self.payload = self.request_object.payload

        self.request_time = request_time
        self.content_length = len(self.raw_response)
        self.row_count = len(self.raw_response.splitlines())
        self.word_count = len(re.findall('[\S]+', self.raw_response))
        self.response_code = response_code

    def rebuild(self, raw_response):
        self.raw_response = raw_response

        self.content_length = len(raw_response)
        self.row_count = len(self.raw_response.splitlines())
        self.word_count = len(re.findall('[\S]+', self.raw_response))

    @staticmethod
    def determine_charsets(raw_response, response_headers):
        """ Пытается определить кодировку по хидерам, ответу и кофейной гуще

        :param raw_response: Сырой ответ в байтах или строкой
        :param response_headers:
        :return:
        """
        content_types = ['utf-8']

        soup = BeautifulSoup(raw_response, 'html.parser')
        meta = soup.find('meta', attrs={'http-equiv': 'Content-Type'})

        if meta is not None:
            meta_content_type = re.search('charset=([\w-]+)', meta['content'])
            if meta_content_type is not None:
                content_type = meta_content_type.group(1)
                if content_type.lower() not in content_types:
                    content_types.append(content_type.lower())

        header = response_headers.get('Content-Type')

        if header is not None:
            header_content_type = re.search('charset=([\w-]+)', response_headers['Content-Type'])
            if header_content_type is not None:
                content_type = header_content_type.group(1)
                if content_type not in content_types:
                    content_types.append(content_type.lower())

        return content_types