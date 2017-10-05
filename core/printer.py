import re
from functools import reduce
from operator import add

from termcolor import colored

from core.comparer import Comparer


class Printer:
    def __init__(self, properties=None, section_name=None):
        self.properties = properties
        self.section_name = section_name

        self.terminal_width = 125
        self.response_id = 0
        # Свойства, которые будут сравниваться при необходимости
        self.comparer = Comparer()
        self.compared_properties = []

        self.format_string = ''
        self.format_separator = '|'
        self.format_size = []

        self.header_string = ''
        self.header_names = []
        self.body_string = ''
        self.bottom_string = ''

        getattr(self, 'init_{}_printer'.format(self._translate_section_name(section_name)))()
        self._build_format_string()

    def init_common_analyzer_printer(self):
        self.compared_properties = ['response_code', 'content_length', 'row_count', 'word_count', 'request_time']

        self.header_names = ['#', 'Код', 'Контент', 'Строки', 'Слова', 'Время', 'Нагрузка']
        self.format_size = ['5', '10', '18', '16', '14', '25', '*'] # * - поделить оставшееся пространство self.terminal_width

    def init_blind_boolean_based_sql_analyzer_printer(self):
        self.compared_properties = ['response_code', 'content_length', 'row_count', 'word_count']

        self.header_names = ['#', 'Код', 'Контент', 'Строки', 'Слова', 'Нагрузка']
        self.format_size = ['5', '10', '18', '16', '14', '*']

    def _build_format_string(self):
        self.format_size = self._calculate_width(self.format_size)

        format_args = reduce(add, zip(self.header_names, self.format_size))
        self.format_string = '{sep}{: ^{}}' * len(self.header_names) + '{sep}'

        self.header_string = self.format_string.format(*format_args, sep=self.format_separator)

    def _calculate_width(self, width):
        x = sum(i == '*' for i in width)
        absolute_width = sum(int(i) for i in width if i.isdigit())

        x = round(
            (self.terminal_width - absolute_width - (len(self.header_names) + 1) * len(self.format_separator)) / x)
        return [int(i) if i.isdigit() else x for i in width]

    def print_head(self):
        self.print_footer()
        print(self.header_string)

    def print_resp_info(self, response_obj):
        standard_response = self.properties['Program']['standard_response']

        self.response_id += 1
        self._print_colored_comparison(standard_response, response_obj)

    def print_result_for_response_group(self, response_group):
        self.print_footer()
        for key in sorted(response_group.keys()):
            response = response_group[key][0]
            self.print_resp_info(response)
        self.print_footer()

    def _print_colored_comparison(self, standard_response, response):
        changes = self.comparer.compare_properties(standard_response, response, self.compared_properties)
        format_body_string = []
        temp_body_size = self.format_size[:]

        for ind, change in enumerate(changes):
            old_result = '{:+}'.format(change[1])
            if change[2] == '=':
                colored_old_result = old_result
            elif change[2] == '>':
                temp_body_size[ind + 1] += 9
                colored_old_result = colored(old_result, 'red')
            else:
                temp_body_size[ind + 1] += 9
                colored_old_result = colored(old_result, 'green')

            format_body_string.append('{} ({:})'.format(change[0], colored_old_result))

        format_body_string = [str(self.response_id)] + format_body_string + [response.test_info]
        body_string = '{sep}' + '{sep}'.join(
            '{: ^{}}'.format(x, size) for x, size in zip(format_body_string, temp_body_size)) \
                      + '{sep}'

        print(body_string.format(sep=self.format_separator))

    def print_footer(self):
        info = '-' * self.terminal_width
        print(info)

    def _translate_section_name(self, section_name):
        return (re.sub('[a-z][A-Z]|[A-Z]{2}(?=[a-z])', lambda x: '_'.join(x.group(0).lower()), section_name)).lower()
