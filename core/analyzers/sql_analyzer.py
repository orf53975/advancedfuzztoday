from core.analyzers.analyzer import Analyzer
from core.printer import Printer
from request_package.requester import Requester
from core.encoder import *
from functools import reduce
from operator import add


class BlindBooleanBasedSqlAnalyzer(Analyzer):
    def __init__(self, properties):
        Analyzer.__init__(self, properties)

        self.printer = Printer(properties, 'BlindBooleanBasedSqlAnalyzer')

        self.blind_sql_and_payloads = self.get_payloads('/fuzzing/sql_blind_and.txt')
        self.blind_sql_or_payloads = self.get_payloads('/fuzzing/sql_blind_or.txt')

        encode_list = [url_encode, double_url_encode, overlong_utf8_encode]
        self.blind_sql_and_payloads = reduce(add, [list(map(encode, self.blind_sql_and_payloads)) for encode in encode_list])
        self.blind_sql_or_payloads = reduce(add, [list(map(encode, self.blind_sql_or_payloads)) for encode in encode_list])

        self.modified_requests = self.get_modified_requests(self.blind_sql_and_payloads + self.blind_sql_or_payloads, flags=5)
        for index, request in enumerate(self.modified_requests):
            request.id = index

    def analyze(self):
        print('[!] Запускаю Blind Boolean Based SqlAnalyzer')
        requester = Requester(self.modified_requests, self.response_queue, self.properties)
        requester.run()

        responses = dict()
        self.printer.print_head()

        while requester.is_running() or not self.response_queue.empty():
            response_obj = self.response_queue.get()
            responses[response_obj.id] = response_obj

            if response_obj.id % 2 == 0:
                index = response_obj.id + 1
            else:
                index = response_obj.id - 1

            if responses.get(index) is not None:
                resp1 = response_obj
                resp2 = responses[index]
                # print("[D] Проверка {} и {} запросов".format(resp1.id, resp2.id))
                self._check_diff(resp1, resp2)

    def _check_diff(self, resp1, resp2):
        if resp1.response_code != resp2.response_code or resp1.content_length != resp2.content_length \
                or resp1.row_count != resp2.row_count or resp1.word_count != resp2.word_count:

            self.printer.print_footer()
            self.printer.print_resp_info(resp1)
            self.printer.print_resp_info(resp2)
            self.printer.print_footer()


