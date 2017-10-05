import codecs

from core.analyzers.common_analyzer import CommonAnalyzer

from request_package.request_object import RequestObject
from core.analyzers.sql_analyzer import BlindBooleanBasedSqlAnalyzer


class Controller:
    def __init__(self, properties):
        # Объявления
        self.properties = properties

        # Здесь запускать анализаторы
        analyzer = CommonAnalyzer(self.properties)
        analyzer.analyze()

        # analyzer = BlindBooleanBasedSqlAnalyzer(self.properties)
        # analyzer.analyze()
