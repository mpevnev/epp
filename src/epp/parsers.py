"""

Parsers module.

This module provides actually useful parsers, as opposed to the bookkeeping
ones in the 'core' module.

"""

from collections import deque
import itertools as itools

import epp.core as core
import epp.errors as error


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
            raise core.ParsingFailure(
                state,
                "Expected an alphanumeric character, got the end of input",
                error.AlnumError.EOI)
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z' or '0' <= char <= '9':
                return state.consume(1)
            raise core.ParsingFailure(
                state,
                f"Expected an alphanumeric character, got '{char}'",
                error.AlnumError.NON_ALNUM)
        if char.isalnum():
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected an alphanumeric character, got '{char}'",
            error.AlnumError.NON_ALNUM)
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
            raise core.ParsingFailure(
                state,
                "Expected an alphabetic character, got the end of input",
                error.AlphaError.EOI)
        if ascii_only:
            if 'a' <= char <= 'z' or 'A' <= char <= 'Z':
                return state.consume(1)
            raise core.ParsingFailure(
                state,
                f"Expected an alphabetic character, got '{char}'",
                error.AlphaError.NON_ALPHA)
        if char.isalpha():
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected an alphabetic character, got '{char}'",
            error.AlphaError.NON_ALPHA)
    return alpha_body


def any_char():
    """ Return a parser that would match any character. """
    def any_char_body(state):
        """ Match a single character. """
        try:
            _ = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure(
                state,
                "Expected a character, got the end of input",
                error.AnyCharError.EOI)
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
            raise core.ParsingFailure(
                state,
                "Expected a character, got the end of input",
                error.CondCharError.EOI)
        if condition(char):
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"{char} did not pass the {condition} test",
            error.CondCharError.DID_NOT_PASS)
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
            raise core.ParsingFailure(
                state,
                "Expected a digit, got the end of input",
                error.DigitError.EOI)
        if '0' <= char <= '9':
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected a digit, got '{char}'",
            error.DigitError.NOT_DIGIT)
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
            raise core.ParsingFailure(
                state,
                "Expected a hexadecimal digit, got the end of input",
                error.HexDigitError.EOI)
        if ('0' <= char <= '9') or ('a' <= char <= 'f') or ('A' <= char <= 'F'):
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected a hexadecimal digit, got '{char}'",
            error.HexDigitError.NOT_DIGIT)
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
            raise core.ParsingFailure(
                state,
                "Expected a newline, got the end of input",
                error.NewlineError.EOI)
        if ord(char) in _LINE_SEPARATORS:
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected a newline, got '{char}'",
            error.NewlineError.NOT_NEWLINE)
    return newline_body


def nonwhite_char():
    """ Return a parser that will match a character of anything but whitespace. """
    def nonwhite_char_body(state):
        """ Match a non-whitespace character. """
        try:
            char = state.string[state.left_start]
        except IndexError:
            raise core.ParsingFailure(
                state,
                "Expected a non-whitespace character, got the end of input",
                error.NonwhiteError.EOI)
        if char.isspace():
            raise core.ParsingFailure(
                state,
                "Got a whitespace character when expecting a non-whitespace one",
                error.NonwhiteError.WHITE)
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
            raise core.ParsingFailure(
                state,
                "Expected a whitespace character, got the end of input",
                error.WhiteCharError.EOI)
        if accept_newlines:
            if char.isspace():
                return state.consume(1)
            raise core.ParsingFailure(
                state,
                f"Expected a whitespace character, got '{char}'",
                error.WhiteCharError.NON_WHITE)
        # not accepting newlines
        if char.isspace():
            if ord(char) in _LINE_SEPARATORS:
                raise core.ParsingFailure(
                    state,
                    f"Got a newline character {hex(ord(char))} when not accepting newlines",
                    error.WhiteCharError.NEWLINE)
            return state.consume(1)
        raise core.ParsingFailure(
            state,
            f"Expected a whitespace character, got '{char}'",
            error.WhiteCharError.NON_WHITE)
    return white_char_body


#--------- aggregates and variations of the above ---------#


def alnum_word(ascii_only=False):
    """
    Return a parser that will match a non-empty sequence of alphanumeric
    character.

    If 'ascii_only' is truthy, match only ASCII characters, otherwise match
    everything that is considered an alphanumeric character in Unicode.
    """
    error_transformer = _mk_aggregate_transformer(
        error.AlnumError.EOI,
        error.AlnumWordError.EOI,
        error.AlnumWordError.NON_ALNUM,
        "Expected an alphanumeric word")
    return core.modify_error(many(alnum(ascii_only), 1), error_transformer)


def alpha_word(ascii_only=False):
    """
    Return a parser that will match a non-empty sequence of alphabetic
    characters.

    If 'ascii_only' is truthy, match only ASCII characters, otherwise match
    everything that is considered an alphabetic character in Unicode.
    """
    error_transformer = _mk_aggregate_transformer(
        error.AlphaError.EOI,
        error.AlphaWordError.EOI,
        error.AlphaWordError.NON_ALPHA,
        "Expected a sequence of alphabetic characters")
    return core.modify_error(many(alpha(ascii_only), 1), error_transformer)


def any_word():
    """
    Return a parser that will match a non-empty sequence of non-whitespace
    characters.
    """
    error_transformer = _mk_aggregate_transformer(
        error.NonwhiteError.EOI,
        error.AnyWordError.EOI,
        error.AnyWordError.WHITE,
        "Expected a sequence of non-whitespace characters")
    return core.modify_error(many(nonwhite_char(), 1), error_transformer)


def hex_int(must_have_prefix=False):
    """
    Return a parser that will match integers in base 16 (with or without '0x'
    prefix).

    If 'must_have_prefix' is truthy, fail if '0x' prefix is omitted.
    """
    def prefix_error_transformer(exc):
        """ Transform the error message about the missing prefix. """
        return core.ParsingFailure(
            exc.state,
            f"Required prefix '0x' is not found in {repr(exc.state.left[:20])}",
            error.HexIntError.NO_PREFIX)
    primary_error_transformer = _mk_aggregate_transformer(
        error.HexDigitError.EOI,
        error.HexIntError.EOI,
        error.HexIntError.NON_HEX_INT,
        "Expected a sequence of hexadecimal digits")
    prefix = literal("0x") if must_have_prefix else maybe(literal("0x"))
    prefix = core.modify_error(prefix, prefix_error_transformer)
    primary = many(hex_digit(), 1)
    primary = core.modify_error(primary, primary_error_transformer)
    return core.chain([prefix, primary])


def integer():
    """
    Return a parser that will match integers in base 10.
    """
    error_transformer = _mk_aggregate_transformer(
        error.DigitError.EOI,
        error.IntegerError.EOI,
        error.IntegerError.NON_INT,
        "Expected a sequence of digits")
    return core.modify_error(many(digit(), 1), error_transformer)


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
            raise core.ParsingFailure(
                state,
                "Expected a line, got an end of input",
                error.LineError.EOI)
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
    def error_transformer(exc):
        """ Transform the error message. """
        if exc.code == error.WhiteCharError.EOI:
            return core.ParsingFailure(
                exc.state,
                "Expected whitespace, got the end of input",
                error.WhitespaceError.EOI)
        if accept_newlines:
            msg = f"Expected at least {min_num} characters of whitespace (and maybe newlines)"
        else:
            msg = f"Expected at least {min_num} characters of whitespace (not newlines)"
        return core.ParsingFailure(
            exc.state,
            f"{msg}, got {repr(exc.state.left[:20])}",
            error.WhitespaceError.NOT_ENOUGH)
    return core.modify_error(many(white_char(accept_newlines), min_num), error_transformer)


#--------- various ---------#


def balanced(opening, closing, include_outer_pair=False):
    """
    Return a parser that will parse everything between an 'opening' string and
    a 'closing' string, where the number of opening and closing strings in the
    parsed part is balanced.

    Fail if the input doesn't start with 'opening' or if there are not enough
    'closing' substrings in the input to balance the opening ones.

    If 'include_outer_pair' is truthy, include the first opening and the last
    closing strings in the 'parsed', otherwise exclude them, leaving just the
    part between them.
    """
    def balanced_body(state):
        """ Match input between balanced pair of strings. """
        open_len = len(opening)
        closing_len = len(closing)
        if state.string[state.left_start:state.left_start + open_len] != opening:
            raise core.ParsingFailure(
                state,
                f"{repr(state.left[0:20])} doesn't start with '{opening}'",
                error.BalancedError.DOESNT_START)
        pos = state.left_start + open_len
        balance = 1
        while pos < state.left_end and balance != 0:
            cur_bit = state.string[pos:state.left_end]
            if cur_bit.startswith(closing):
                balance -= 1
                pos += closing_len
                continue
            if cur_bit.startswith(opening):
                balance += 1
                pos += open_len
                continue
            pos += 1
        if balance != 0:
            raise core.ParsingFailure(
                state,
                f"Failed to find a balanced pair of '{opening}' and '{closing}'",
                error.BalancedError.NO_PAIR)
        if include_outer_pair:
            return state._replace(
                left_start=pos,
                parsed_start=state.left_start,
                parsed_end=pos)
        return state._replace(
            left_start=pos,
            parsed_start=state.left_start + open_len,
            parsed_end=pos - closing_len)
    return balanced_body


def end_of_input():
    """ Return a parser that matches only if there is no input left. """
    def end_of_input_body(state):
        """ Match the end of input. """
        if state.left_start == state.left_end:
            return state._replace()
        raise core.ParsingFailure(
            state,
            f"Expected the end of input, got {repr(state.left[0:20])}",
            error.EndOfInputError.NOT_END)
    return end_of_input_body


def everything():
    """ Return a parser that consumes all remaining input. """
    def everything_body(state):
        """ Consume all remaining input. """
        return state._replace(
            parsed_start=state.left_start,
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
            raise core.ParsingFailure(
                state,
                f"{repr(state.left[:20])} doesn't start with {lit}",
                error.LiteralError.SHORTER)
        i = -1
        for i, char in enumerate(lit):
            if char != state.string[state.left_start + i]:
                raise core.ParsingFailure(
                    state,
                    f"'{repr(state.left[:20])} doesn't start with {lit}",
                    error.LiteralError.DOESNT_START)
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
            return state._replace(
                parsed_start=state.left_start,
                parsed_end=state.left_start)
    return core.copy_lookahead(parser, maybe_body)


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
        must = core.chain(itools.repeat(parser, min_hits), combine)
    else:
        must = None
    if max_hits > 0:
        might = core.chain(itools.repeat(parser, max_hits - min_hits),
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
    def error_transformer(exc):
        """ Transform the error message. """
        return core.ParsingFailure(
            exc.state,
            f"None of the literals matched the input: {repr(exc.state.left[:20])}'",
            error.MultiError.ALL_FAILED)
    return core.modify_error(core.branch(map(literal, literals)), error_transformer)


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
            window = state.string[window_start:window_end]
            if cond(state, window):
                rep += 1
                continue
            if rep < min_repetitions:
                msg = "Failed to achieve required minimum of repetitions " \
                      f"on input: {repr(state.left[:20])}'"
                raise core.ParsingFailure(state, msg, error.RepeatWhileError.NOT_ENOUGH)
            if combine:
                return state._replace(
                    left_start=window_start,
                    parsed_start=start,
                    parsed_end=window_start)
            return state._replace(
                left_start=window_start,
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
            msg = "Less than requested number of characters received on input: " \
                  f"{repr(state.left[:20])}'"
            raise core.ParsingFailure(state, msg, error.TakeError.NOT_ENOUGH)
        return state.consume(min(num, state.left_len))
    return take_body


def weave(parsers, separator, trailing=None, stop_on_failure=False):
    """
    Return a chain where each parser in 'parsers' is separated by 'separator'
    from others.

    If 'trailing' is not None, append it to the resulting chain.

    'stop_on_failure' will be sent through to the underlying 'chain' generator.
    """
    parsers = iter(parsers)
    saved = deque()
    def iterator():
        """ Return the iterable that will go into the chain. """
        saved_len = len(saved)
        for i, p in enumerate(itools.chain(saved, parsers)):
            if i != 0:
                yield separator
            if i >= saved_len:
                saved.append(p)
            yield p
        if trailing is not None:
            yield trailing
    return core.chain(core.reuse_iter(iterator), stop_on_failure=stop_on_failure)


#--------- helper things ---------#


_LINE_SEPARATORS = [0x000a, 0x000d, 0x001c, 0x001d, 0x001e, 0x0085, 0x2028, 0x2029]


def _mk_aggregate_transformer(
        eoi_code_in,
        eoi_code_out,
        generic_code_out,
        msg):
    """ Create an error transformer for aggregate functions. """
    def transformer(exc):
        """ Transform the error message. """
        if exc.code == eoi_code_in:
            return core.ParsingFailure(
                exc.state,
                f"{msg}, got the end of input",
                eoi_code_out)
        return core.ParsingFailure(
            exc.state,
            f"{msg}, got {repr(exc.state.left[:20])}",
            generic_code_out)
    return transformer
