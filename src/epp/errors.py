"""
Error module.

Provides error codes for parsers in 'core' and 'parsers'.
"""

from enum import Enum, auto


#--------- error codes for core parsers ---------#


class BranchError(Enum):
    """ Error codes for 'branch' parsers. """
    ALL_FAILED = auto()
    EMPTY = auto()


class ChainError(Enum):
    """ Error codes for 'chain' parsers. """
    LOOKAHEAD_FAILED = auto()


class FailError(Enum):
    """ Error codes for 'fail' parsers. """
    FAILED = auto()


class SubparseError(Enum):
    """ Error codes for 'subparse' parsers. """
    FAILED = auto()


class TestError(Enum):
    """ Error codes for 'test' parsers. """
    FAILED = auto()


#--------- error codes for single-character parsers ---------#


class AlnumError(Enum):
    """ Error codes for 'alnum' parsers. """
    EOI = auto()
    NON_ALNUM = auto()


class AlphaError(Enum):
    """ Error codes for 'alpha' parsers. """
    EOI = auto()
    NON_ALPHA = auto()


class AnyCharError(Enum):
    """ Error codes for 'any_char' parsers. """
    EOI = auto()


class CondCharError(Enum):
    """ Error codes for 'cond_char' parsers. """
    EOI = auto()
    DID_NOT_PASS = auto()


class DigitError(Enum):
    """ Error codes for 'digit' parsers. """
    EOI = auto()
    NOT_DIGIT = auto()


class HexDigitError(Enum):
    """ Error codes for 'hex_digit' parsers. """
    EOI = auto()
    NOT_DIGIT = auto()


class NewlineError(Enum):
    """ Error codes for 'newline' parsers. """
    EOI = auto()
    NOT_NEWLINE = auto()


class NonwhiteError(Enum):
    """ Error codes for 'nonwhite_char' parsers. """
    EOI = auto()
    WHITE = auto()


class WhiteCharError(Enum):
    """ Error codes for 'white_char' parsers. """
    EOI = auto()
    NON_WHITE = auto()
    NEWLINE = auto()


#--------- error codes for aggregates of single-character parsers ---------#


class AlnumWordError(Enum):
    """ Error codes for 'alnum_word' parsers. """
    EOI = auto()
    NON_ALNUM = auto()


class AlphaWordError(Enum):
    """ Error codes for 'alpha_word' parsers. """
    EOI = auto()
    NON_ALPHA = auto()


class AnyWordError(Enum):
    """ Error codes for 'any_word' parsers. """
    EOI = auto()
    WHITE = auto()


class HexIntError(Enum):
    """ Error codes for 'hex_int' parsers. """
    EOI = auto()
    NON_HEX_INT = auto()
    NO_PREFIX = auto()


class IntegerError(Enum):
    """ Error codes for 'integer' parsers. """
    EOI = auto()
    NON_INT = auto()


class LineError(Enum):
    """ Error codes for 'line' parsers. """
    EOI = auto()


class WhitespaceError(Enum):
    """ Error codes for 'whitespace' parsers. """
    EOI = auto()
    NOT_ENOUGH = auto()


#--------- error codes for various parsers ---------#


class BalancedError(Enum):
    """ Error codes for 'balanced' parsers. """
    DOESNT_START = auto()
    NO_PAIR = auto()


class EndOfInputError(Enum):
    """ Error codes for 'end_of_input' parsers. """
    NOT_END = auto()


class LiteralError(Enum):
    """ Error codes for 'literal' parsers. """
    SHORTER = auto()
    DOESNT_START = auto()


class MultiError(Enum):
    """ Error codes for 'multi' parsers. """
    ALL_FAILED = auto()


class RepeatWhileError(Enum):
    """ Error codes for 'repeat_while' parsers. """
    NOT_ENOUGH = auto()


class TakeError(Enum):
    """ Error codes for 'take' parsers. """
    NOT_ENOUGH = auto()
