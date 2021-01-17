"""
Common json encoders
"""
from datetime import datetime
from json import JSONEncoder


class DateTimeEncoder(JSONEncoder):
    """ JSON encoder for datetime class """

    def default(self, o):  # pylint: disable=method-hidden
        """
        Overriding for specific serialization
        """
        if isinstance(o, datetime):
            return str(o)
        return super(DateTimeEncoder, self).default(o)
