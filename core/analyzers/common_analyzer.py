from collections import defaultdict
from functools import reduce
from operator import add

from core.analyzers.analyzer import Analyzer
from core.encoder import *
from core.printer import Printer
from request_package.requester import Requester


class CommonAnalyzer(Analyzer):
    def __init__(self, properties):
        Analyzer.__init__(self, properties)
        self.printer = Printer(properties, 'CommonAnalyzer')

        self.detect_reflected_patterns()
        self.clean_reflected_rows(self.standard_response)

    def analyze(self):
        # TODO: ИСПРАВИТЬ !!!
        # common_payloads = self.get_payloads(self.properties['Main']['wordlist'])
        common_payloads = self.get_payloads('fuzzing/test.txt')
        response_dict = defaultdict(lambda: defaultdict(list))

        encode_list = [url_encode, double_url_encode, overlong_utf8_encode]
        modified_request_groups = self.get_modified_request_groups(common_payloads, encode_list)
        modified_requests = reduce(add, zip(*modified_request_groups))


        # self.print_standard_resp_info()

        requester = Requester(modified_requests, self.response_queue, self.properties)
        requester.run()

        self.printer.print_head()

        while requester.is_running() or not self.response_queue.empty():
            response_obj = self.response_queue.get()
            # self.clean_reflected_rows(response_obj)
            response_dict[response_obj.gid][response_obj.id].append(response_obj)

            if len(response_dict[response_obj.gid].keys()) == len(encode_list) and \
                    any(self.is_interesting_behavior(response_dict[response_obj.gid][key][0]) for key in response_dict[response_obj.gid].keys()):
                self.printer.print_result_for_response_group(response_dict[response_obj.gid])
