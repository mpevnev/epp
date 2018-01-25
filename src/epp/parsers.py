"""

Parsers module.

This module provides actually useful parsers, as opposed to the bookkeeping
ones in the 'core' module.

"""

from collections import deque

import epp.core as core
# reimport everything from 'core' to avoid having to import both 'core' and 'parsers'
from epp.core import *


#--------- single-character parsers ---------#


def alnum(ascii_only=False):
    """
    Return a parser that will match a single alphanumeric character.

    If 'ascii_only' is truthy, match only ASCII alphanumeric characters
    ([a-zA-Z0-9]), not whatever makes .isalnum() return True.
    """
    def res(state):
        """ Match an alphanumeric character. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected an alphanumeric character, got the end of input")
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z' or '0' <= char <= '9':
                return state.consume(1)
            raise core.ParsingFailure(f"Expected an alphanumeric character, got '{char}'")
        if char.isalnum():
            return state.consume(1)
        raise core.ParsingFailure(f"Expected an alphanumeric character, got '{char}'")
    return res


def alpha(ascii_only=False):
    """
    Return a parser that will match a single alphabetic character.

    If 'ascii_only' is truthy, match only ASCII alphabetic characters, not
    everything for which .isalpha() returns True.
    """
    def res(state):
        """ Match an alphabetic character. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected an alphabetic character, got the end of input")
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z':
                return state.consume(1)
            raise core.ParsingFailure(f"Expected an alphabetic character, got '{char}'")
        if char.isalpha():
            return state.consume(1)
        raise core.ParsingFailure(f"Expected an alphabetic character, got '{char}'")
    return res


def any_char():
    """ Return a parser that would match any character. """
    def res(state):
        """ Match a single character. """
        try:
            _ = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected a character, got the end of input")
        return state.consume(1)
    return res


def digit():
    """
    Return a parser that would match a single decimal digit.
    """
    def res(state):
        """ Parse a single decimal digit. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected a digit, got the end of input")
        if '0' <= char <= '9':
            return state.consume(1)
        raise core.ParsingFailure(f"Expected a digit, got '{char}'")
    return res


def newline():
    """
    Return a parser that will match a newline character.

    For Windows users: this will match a single \\r or \\n from a \\n\\r pair.
    """
    def res(state):
        """ Parse a newline character. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected a newline, got the end of input")
        if ord(char) in _LINE_SEPARATORS:
            return state.consume(1)
        raise core.ParsingFailure(f"Expected a newline, got '{char}'")
    return res


def nonwhite_char():
    """ Return a parser that will match a character of anything but whitespace. """
    def res(state):
        """ Match a non-whitespace character. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure(
                "Expected a non-whitespace character, got the end of input")
        if char.isspace():
            raise core.ParsingFailure(
                "Got a whitespace character when expecting a non-whitespace one")
        return state.consume(1)
    return res


def white_char(accept_newlines=False):
    """
    Return a parser that will match a character of whitespace, optionally also
    matching newline characters.
    """
    def res(state):
        """ Match a character of whitespace. """
        try:
            char = state.left[0]
        except IndexError:
            raise core.ParsingFailure("Expected a whitespace character, got the end of input")
        if accept_newlines:
            if char.isspace():
                return state.consume(1)
            else:
                raise core.ParsingFailure(f"Expected a whitespace character, got '{char}'")
        else:
            if char.isspace():
                if ord(char) in _LINE_SEPARATORS:
                    raise core.ParsingFailure(
                        f"Got a newline character {hex(ord(char))} when not accepting newlines")
                return state.consume(1)
            else:
                raise core.ParsingFailure(f"Expected a whitespace character, got '{char}'")
    return res


#--------- aggregates and variations of the above ---------#


def integer(alter_state=False):
    """
    Return a parser that will match integers in base 10.

    If 'alter_state' is set to a true value, replace state's value with the
    parsed integer, otherwise leave it alone.
    """
    res = many(digit(), 1)
    if alter_state:
        res = core.chain([res, core.modify(lambda s: s.set(value=int(s.parsed)))])
    return res


def line(keep_newline=False):
    """
    Return a parser that will match a line terminated by a newline.

    If 'keep_newline' is truthy, the terminating newline will be retained in
    the 'parsed' field of the resulting State object, otherwise it won't be.
    The newline is removed from the input in any case.
    """
    def res(state):
        """ Match a line optionally terminated by a newline character. """
        pos = 0
        length = len(state.left)
        if length == 0:
            raise core.ParsingFailure("Expected a line, got an end of input")
        while pos < length:
            char = state.left[pos]
            if ord(char) in _LINE_SEPARATORS:
                if keep_newline:
                    pos += 1
                break
            pos += 1
        if keep_newline:
            return state.consume(pos)
        output = state.set(parsed=state.left[:pos], left=state.left[pos+1:])
        return output
    return res


#--------- various ---------#


def everything():
    """ Return a parser that consumes all remaining input. """
    def res(state):
        """ Consume all remaining input. """
        output = state.copy()
        output.left = ""
        output.parsed = state.left
        return output
    return res


def literal(lit):
    """
    Return a parser that will match a given literal and remove it from input.
    """
    def res(state):
        """ Match a literal. """
        if state.left.startswith(lit):
            return state.set(left=state.left[len(lit):], parsed=lit)
        raise core.ParsingFailure(f"'{state.left[0:20]}' doesn't start with '{lit}'")
    return res


def maybe(parser):
    """
    Return a parser that will match whatever 'parser' matches, and if 'parser'
    fails, matches and consumes nothing.
    """
    def res(state):
        """
        Match whatever another parser matches, or consume no input if it fails.
        """
        try:
            return parser(state)
        except core.ParsingFailure:
            return state.copy()
    return res


def many(parser, min_hits=0, max_hits=0, combine=True):
    """
    Return a parser that will run 'parser' on input repeatedly until it fails.

    If 'min_hits' is above zero, fail if 'parser' was run successfully less
    than 'min_hits' times.

    If 'max_hits' is above zero, stop after 'parser' was run successfully
    'max_hits' times.

    If 'combine' is truthy, set 'parsed' of the resulting state object to
    concatenation of individually matched strings, otherwise set it to the last
    matched string.

    Raise ValueError if 'max_hits' is above zero and is less than 'min_hits'.
    """
    if min_hits < 0:
        min_hits = 0
    if max_hits < 0:
        max_hits = 0
    if max_hits > 0 and max_hits < min_hits:
        raise ValueError("'max_hits' is less than 'min_hits'")
    def res(state):
        """ Run a parser several times. """
        pieces = deque()
        for _ in range(min_hits):
            state = parser(state)
        if combine:
            pieces.append(state.parsed)
        # notice that there's no exception handling here - this way a
        # thrown exception terminates 'many', which is exactly what we need.
        i = min_hits
        while max_hits == 0 or i < max_hits:
            try:
                state = parser(state)
                if combine:
                    pieces.append(state.parsed)
            except core.ParsingFailure:
                if combine:
                    state.parsed = "".join(pieces)
                return state
            i += 1
        if combine:
            state.parsed = "".join(pieces)
        return state
    return res


def multi(literals):
    """
    Return a parser that will match any of given literals.
    """
    def res(state):
        """ Match any of given literals. """
        for lit in literals:
            if state.left.startswith(lit):
                return state.set(left=state.left[len(lit):], parsed=lit)
        anyof = ", ".join(map(lambda s: f"\"{s}\"", literals))
        raise core.ParsingFailure(f"'{state.left[0:20]}' doesn't start with any of ({anyof})")
    return res


def repeat_while(cond, window_size=1, min_repetitions=0, combine=True):
    """
    Return a parser that will call
    > cond(state, state.left[:window_size])
    repeatedly consuming 'window_size' characters from the input, until 'cond'
    returns a falsey value. Note that the last window may be less than
    'window_size' characters long.

    If 'min_repetitions' is above 0 and less than that many windows were
    processed, fail.

    If 'combine' is truthy, set 'parsed' of the resulting State object to a
    concatenation of processed windows, otherwise set it to the last window.
    """
    if window_size <= 0:
        raise ValueError("A non-positive 'window_size'")
    def res(state):
        """ Repeatedly check a condition on windows of given width. """
        state = state.copy()
        i = 0
        pos = 0
        while state.left != "":
            window = state.left[pos:pos + window_size]
            if not cond(state, window):
                if i < min_repetitions:
                    raise core.ParsingFailure("Less than requested minimum of repetitions achieved")
                if i > 0:
                    if combine:
                        state.parsed = state.left[0:pos]
                    else:
                        state.parsed = state.left[pos - window_size:pos]
                else:
                    state.parsed = ""
                state.left = state.left[pos:]
                return state
            i += 1
            pos += window_size
        if i < min_repetitions:
            raise core.ParsingFailure("Less than requested minimum of repetitions achieved.")
        if i > 0:
            if combine:
                state.parsed = state.left[0:pos]
            else:
                state.parsed = state.left[pos - window_size:pos]
        else:
            state.parsed = ""
        return state
    return res


#--------- helper things ---------#

_LINE_SEPARATORS = [0x000a, 0x000d, 0x001c, 0x001d, 0x001e, 0x0085, 0x2028, 0x2029]
