import re
from collections import namedtuple
from django.core.exceptions import ValidationError
from django.db import models

_Span = namedtuple('_Span', ['doc_id', 'char_begin', 'char_end'])
class Span(_Span):
    @classmethod
    def from_str(cls, value):
        span_re = re.compile(r"\(([a-zA-Z0-9._]+),([0-9]+),([0-9]+)\)")
        match = span_re.match(value)
        if match is None:
            raise ValidationError("Invalid span string: {}".format(value))
        doc_id, char_begin, char_end = match.groups()
        return cls(doc_id, int(char_begin), int(char_end))

    def __str__(self):
        return "({},{},{})".format(self.doc_id, self.char_begin, self.char_end)

class SpanField(models.Field):
    description = "A provenance span"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def db_type(self, connection):
        return 'span'

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        else:
            return Span.from_str(value)

    def to_python(self, value):
        if isinstance(value, Span):
            return value
        elif value is None:
            return value
        else:
            return Span.from_str(value)
    def get_prep_value(self, value):
        return str(value)

_Score = namedtuple('_Score', ['precision', 'recall', 'f1'])
class Score(_Score):
    @classmethod
    def from_str(cls, value):
        score_re = re.compile(r"\(([0-9]*\.?[0-9]+),([0-9]*\.?[0-9]+),([0-9]*\.?[0-9]+)\)")
        match = score_re.match(value)
        if match is None:
            raise ValidationError("Invalid span string: {}".format(value))
        precision, recall, f1 = match.groups()
        return cls(float(precision), float(recall), float(f1))

    def __str__(self):
        return "({},{},{})".format(self.precision, self.recall, self.f1)

class ScoreField(models.Field):
    description = "A score"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    def db_type(self, connection):
        return 'span'

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return None
        else:
            return Score.from_str(value)

    def to_python(self, value):
        if isinstance(value, Score):
            return value
        elif value is None:
            return value
        else:
            return Score.from_str(value)
    def get_prep_value(self, value):
        return str(value)

