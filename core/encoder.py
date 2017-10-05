import re
import string
from urllib.parse import quote


def str_to_bytes(payload):
    """ Конвертирует строку в байты

    Посимвольно переводит вхоную строку в байты в формате utf8.
    Символы формата %[\da-fA-F]{2} транслирует в байт
    :param payload:
    :return: объект bytes
    """
    if isinstance(payload, (bytes, bytearray)):
        return payload

    index, payload_len = 0, len(payload)
    hexadecimal = set(string.hexdigits)
    buffer = []

    while index < payload_len:
        current_char = payload[index]

        # Особым образом обрабатываем последовательность %[\da-fA-F]{2}
        if current_char == '%' and index + 2 < payload_len:
            possibly_byte = payload[index+1:index+3]

            # Проверяем срез на принадлежность к hexadecimal
            if not set(possibly_byte) - hexadecimal:
                buffer.append(int(possibly_byte, 16))
            else:
                buffer += [ord(x) for x in payload[index:index+3]]
            index += 3
        else:
            buffer += current_char.encode()
            index += 1

    return bytes(buffer)


def no_encode(payload):
    return payload


def url_encode(payload):
    payload = str_to_bytes(payload)
    return quote(payload)


def double_url_encode(payload):
    payload = str_to_bytes(payload)
    return quote(quote(payload))


# TODO: доработать
def unicode_encode(payload):
    payload = str_to_bytes(payload)


def decimal_html_encode(payload):
    payload = str_to_bytes(payload)
    return url_encode(''.join(map(lambda x: '&#{:0>7}'.format(x), payload)))


def hexadecimal_html_encode(payload):
    payload = str_to_bytes(payload)
    return url_encode(''.join(map(lambda x: '&#x{:0>2}'.format(hex(x)[2:]), payload)))


def overlong_utf8_encode(payload):
    buffer = bytearray()
    excluded_chars = set(ord(x) for x in (string.ascii_letters + string.digits))

    payload = str_to_bytes(payload)

    for ord_char in payload:
        if ord_char < 128 and ord_char not in excluded_chars:
            new_char = [int('11000000', 2), int('10000000', 2)]
            new_char = bytearray([new_char[0] | (ord_char >> 6), new_char[1] | (ord_char & 63)])
            buffer += new_char
        else:
            buffer += chr(ord_char).encode()

    return url_encode(buffer)


if __name__ == '__main__':
    with open('../payloads/fuzzing/metacharacters.txt') as f:
        s = f.read().splitlines()

