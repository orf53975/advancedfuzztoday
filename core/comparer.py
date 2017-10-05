class Comparer:
    def __init__(self):
        self.results = []

    def compare_properties(self, old_response, new_response, compared_properties):
        """ Сравнивает свойства compared_properties между объектами old_response и new_response

        :param old_response: объект ResponseObject, символизирующий "было"
        :param new_response: объект ResponseObject, символизирующий "стало"
        :param compared_properties: list названий свойств, сравнение которых нужно провести
        :return: list, содержащий кортеж (new_param, old_param, sigh), где sign - элемент из ['=', '>', '<'], показывающий, в какую сторону произошли изменения
        """
        self.results = []
        for prop in compared_properties:
            getattr(self, '_compare_'+prop)(old_response, new_response)

        return self.results

    def _compare_response_code(self, old_response, new_response):
        old_code, new_code = old_response.response_code, new_response.response_code
        if old_code == new_code:
            self.results.append((new_code, old_code, '='))
        elif new_code > old_code:
            self.results.append((new_code, old_code, '>'))
        else:
            self.results.append((new_code, old_code, '<'))

    def _compare_content_length(self, old_response, new_response):
        old_content, new_content = old_response.content_length, new_response.content_length
        if old_content == new_content:
            self.results.append((new_content, 0, '='))
        elif new_content > old_content:
            self.results.append((new_content, new_content - old_content, '>'))
        else:
            self.results.append((new_content, new_content - old_content, '<'))

    def _compare_row_count(self, old_response, new_response):
        old_row_count, new_row_count = old_response.row_count, new_response.row_count
        if old_row_count == new_row_count:
            self.results.append((new_row_count, 0, '='))
        elif new_row_count > old_row_count:
            self.results.append((new_row_count, new_row_count - old_row_count, '>'))
        else:
            self.results.append((new_row_count, new_row_count - old_row_count, '<'))

    def _compare_word_count(self, old_response, new_response):
        old_word_count, new_word_count = old_response.word_count, new_response.word_count
        if old_word_count == new_word_count:
            self.results.append((new_word_count, 0, '='))
        elif new_word_count > old_word_count:
            self.results.append((new_word_count, new_word_count - old_word_count, '>'))
        else:
            self.results.append((new_word_count, new_word_count - old_word_count, '<'))

    def _compare_request_time(self, old_response, new_response):
        old_time, new_time = round(old_response.request_time, 3), round(new_response.request_time, 3)
        if old_time == new_time:
            self.results.append((new_time, 0, '='))
        elif new_time > old_time:
            self.results.append((new_time, round(new_time - old_time, 3), '>'))
        else:
            self.results.append((new_time, round(new_time - old_time, 3), '<'))
