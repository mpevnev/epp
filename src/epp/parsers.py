"""

Parsers module.

This module provides actually useful parsers, as opposed to the bookkeeping
ones in the 'core' module.

"""

import itertools as itools

import epp.core as core


#--------- single-character parsers ---------#


def alnum(ascii_only=False):
    """
    Return a parser that will match a single alphanumeric character.

    If 'ascii_only' is truthy, match only ASCII alphanumeric characters
    ([a-zA-Z0-9]), not whatever makes .isalnum() return True.
    """
    def alnum_body(state):
        """ Match an alphanumeric character. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected an alphanumeric character, got the end of input")
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z' or '0' <= char <= '9':
                return state.consume(1)
            raise core.ParsingFailure(f"Expected an alphanumeric character, got '{char}'")
        if char.isalnum():
            return state.consume(1)
        raise core.ParsingFailure(f"Expected an alphanumeric character, got '{char}'")
    return alnum_body


def alpha(ascii_only=False):
    """
    Return a parser that will match a single alphabetic character.

    If 'ascii_only' is truthy, match only ASCII alphabetic characters, not
    everything for which .isalpha() returns True.
    """
    def alpha_body(state):
        """ Match an alphabetic character. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected an alphabetic character, got the end of input")
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z':
                return state.consume(1)
            raise core.ParsingFailure(f"Expected an alphabetic character, got '{char}'")
        if char.isalpha():
            return state.consume(1)
        raise core.ParsingFailure(f"Expected an alphabetic character, got '{char}'")
    return alpha_body


def any_char():
    """ Return a parser that would match any character. """
    def any_char_body(state):
        """ Match a single character. """
        try:
            _ = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected a character, got the end of input")
        return state.consume(1)
    return any_char_body


def cond_char(condition):
    """
    Return a parser that will match a character such that 'condition(char)' is
    truthy.

    Raise ValueError if 'condition' is not callable.
    """
    if not callable(condition):
        raise ValueError(f"{condition} is not callable")
    def cond_char_body(state):
        """ Match a character that passes a conditional check. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected a character, got the end of input")
        if condition(char):
            return state.consume(1)
        raise core.ParsingFailure(f"{char} did not pass the {condition} test")
    return cond_char_body


def digit():
    """
    Return a parser that would match a single decimal digit.
    """
    def digit_body(state):
        """ Parse a single decimal digit. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected a digit, got the end of input")
        if '0' <= char <= '9':
            return state.consume(1)
        raise core.ParsingFailure(f"Expected a digit, got '{char}'")
    return digit_body


def hex_digit():
    """
    Return a parser that matches a single hexadecimal digit.
    """
    def hex_digit_body(state):
        """ Parse a single hexadecimal digit. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected a hexadecimal digit, got the end of input")
        if ('0' <= char <= '9') or ('a' <= char <= 'f') or ('A' <= char <= 'F'):
            return state.consume(1)
        raise core.ParsingFailure(f"Expected a hexadecimal digit, got '{char}'")
    return hex_digit_body


def newline():
    """
    Return a parser that will match a newline character.

    For Windows users: this will match a single \\r or \\n from a \\n\\r pair.
    """
    def newline_body(state):
        """ Parse a newline character. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure("Expected a newline, got the end of input")
        if ord(char) in _LINE_SEPARATORS:
            return state.consume(1)
        raise core.ParsingFailure(f"Expected a newline, got '{char}'")
    return newline_body


def nonwhite_char():
    """ Return a parser that will match a character of anything but whitespace. """
    def nonwhite_char_body(state):
        """ Match a non-whitespace character. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure(
                "Expected a non-whitespace character, got the end of input")
        if char.isspace():
            raise core.ParsingFailure(
                "Got a whitespace character when expecting a non-whitespace one")
        return state.consume(1)
    return nonwhite_char_body


def white_char(accept_newlines=False):
    """
    Return a parser that will match a character of whitespace, optionally also
    matching newline characters.
    """
    def white_char_body(state):
        """ Match a character of whitespace. """
        try:
            char = state.string[state.left_start]
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
    return white_char_body


#--------- aggregates and variations of the above ---------#


def hex_int(must_have_prefix=False):
    """
    Return a parser that will match integers in base 16 (with or without '0x'
    prefix).

    If 'must_have_prefix' is truthy, fail if '0x' prefix is omitted.
    """
    primary = many(hex_digit(), 1)
    prefix = literal("0x") if must_have_prefix else maybe(literal("0x"))
    return core.chain([prefix, primary])


def integer():
    """
    Return a parser that will match integers in base 10.
    """
    return many(digit(), 1)


def line(include_newline=False):
    """
    Return a parser that will match a line terminated by a newline.

    If 'include_newline' is truthy, 'parsed' window will contain the
    terminating newline, otherwise it will not.
    """
    def line_body(state):
        """ Match a line optionally terminated by a newline character. """
        pos = 0
        length = state.left_len
        if length == 0:
            raise core.ParsingFailure("Expected a line, got an end of input")
        while pos < length:
            char = state.string[state.left_start + pos]
            if ord(char) in _LINE_SEPARATORS:
                if include_newline:
                    return state.consume(pos + 1)
                return state._replace(
                    left_start=state.left_start + pos + 1,
                    parsed_start=state.left_start,
                    parsed_end=state.left_start + pos)
            pos += 1
        return state.consume(length)
    return line_body


def whitespace(min_num=1, accept_newlines=False):
    """
    Return a parser that will consume at least 'min_num' whitespace characters,
    optionally with newlines as well.
    """
    return many(white_char(accept_newlines), min_num)


#--------- various ---------#


def end_of_input():
    """ Return a parser that matches only if there is no input left. """
    def end_of_input_body(state):
        """ Match the end of input. """
        if state.left_start == state.left_end:
            return state._replace()
        raise core.ParsingFailure(f"Expected the end of input, got '{state.left[0:20]}'")
    return end_of_input_body


def everything():
    """ Return a parser that consumes all remaining input. """
    def everything_body(state):
        """ Consume all remaining input. """
        return state._replace(parsed_start=state.left_start,
                              parsed_end=state.left_end,
                              left_start=state.left_end)
    return everything_body


def literal(lit):
    """
    Return a parser that will match a given literal and remove it from input.
    """
    def literal_body(state):
        """ Match a literal. """
        if state.left_len < len(lit):
            raise core.ParsingFailure(f"'{state.left[0:20]}' doesn't start with {lit}")
        i = -1
        for i, char in enumerate(lit):
            if char != state.string[state.left_start + i]:
                raise core.ParsingFailure(f"'{state.left[0:20]}' doesn't start with {lit}")
        return state.consume(i + 1)
    return literal_body


def maybe(parser):
    """
    Return a parser that will match whatever 'parser' matches, and if 'parser'
    fails, matches and consumes nothing.
    """
    def maybe_body(state):
        """
        Match whatever another parser matches, or consume no input if it fails.
        """
        try:
            return parser(state)
        except core.ParsingFailure:
            return state._replace(parsed_start=state.left_start,
                                  parsed_end=state.left_start)
    return maybe_body


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
    if min_hits > 0:
        must = core.chain(core.reuse_iter(itools.repeat, parser, min_hits), combine)
    else:
        must = None
    if max_hits > 0:
        might = core.chain(core.reuse_iter(itools.repeat, parser, max_hits - min_hits),
                           combine=combine,
                           stop_on_failure=True)
    else:
        might = core.chain(itools.repeat(parser), combine, True)
    if must is None:
        return might
    return core.chain([must, might], combine)


def multi(literals):
    """
    Return a parser that will match any of given literals.
    """
    return core.branch(core.reuse_iter(map, literal, literals))


def repeat_while(cond, window_size=1, min_repetitions=0, combine=True):
    """
    Return a parser that will call
    > cond(state, state[:window_size])
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
    def repeat_while_body(state):
        """ Repeatedly check a condition on windows of given width. """
        start = state.left_start
        rep = 0
        while True:
            window_start = state.left_start + rep * window_size
            window_end = window_start + window_size
            window = state.left[window_start:window_end]
            if cond(state, window):
                rep += 1
                continue
            if rep < min_repetitions:
                raise core.ParsingFailure("Failed to achieve required minimum of repetitions")
            if combine:
                return state._replace(left_start=window_start,
                                      parsed_start=start,
                                      parsed_end=window_start)
            return state._replace(left_start=window_start,
                                  parsed_start=window_start - window_size,
                                  parsed_end=window_start)
    return repeat_while_body


def take(num, fail_on_fewer=True):
    """
    Return a parser that will consume exactly 'num' characters.

    If 'fail_on_fewer' is truthy, fail if fewer than 'num' characters are
    available.

    Raise ValueError if 'num' is negative.
    """
    if num < 0:
        raise ValueError("Negative number of consumed characters")
    def take_body(state):
        """ Consume a fixed number of characters. """
        if fail_on_fewer and state.left_len < num:
            raise core.ParsingFailure(f"Less than requested number of characters received")
        return state.consume(min(num, state.left_len))
    return take_body


def weave(parsers, separator, trailing=None):
    """
    Return a chain where each parser in 'parsers' is separated by 'separator'
    from others.
    If 'trailing' is not None, append it to the resulting chain.

    The same note about using iterators as on 'chain' applies here as well.
    Wrap them in a list or 'reuse_iter' if the chain is going to be tried
    several times.
    """
    def iterator():
        """ Return the iterable that will go into the chain. """
        it = iter(parsers)
        for i, p in enumerate(it):
            if i != 0:
                yield separator
            yield p
        if trailing is not None:
            yield trailing
    return core.chain(core.reuse_iter(iterator))


#--------- helper things ---------#

_LINE_SEPARATORS = [0x000a, 0x000d, 0x001c, 0x001d, 0x001e, 0x0085, 0x2028, 0x2029]
