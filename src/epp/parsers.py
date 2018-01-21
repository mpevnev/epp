"""

Parsers module.

This module provides actually useful parsers, as opposed to the bookkeeping
ones in the 'core' module.

"""

from collections import deque

import epp.core as core

#--------- concrete parsers ---------#

def everything():
    """ Return a parser that consumes all remaining input. """
    def res(state):
        """ Consume all remaining input. """
        output = state.copy()
        output.left = ""
        output.parsed = state.left
        return output
    return res

def integer(alter_state=False):
    """
    Return a parser that will match integers in base 10.

    If 'alter_state' is set to a true value, replace state's value with the
    parsed integer, otherwise leave it alone.
    """
    def res(state):
        """ Match an integer. """
        zero = ord("0")
        nine = ord("9")
        length = len(state.left)
        consumed = 0
        for consumed in range(length):
            curchar = state.left[consumed]
            if not zero <= ord(curchar) <= nine:
                break
        if consumed == 0:
            raise core.ParsingFailure("'{state.left[0:20]}' doesn't start with an integer")
        output = state.consume(consumed)
        if alter_state:
            output.value = int(state.left[:consumed])
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
            # thrown exception terminates 'many', which is exactly what we need
            # here.
        for _ in range(min_hits, max_hits):
            try:
                state = parser(state)
                if combine:
                    pieces.append(state.parsed)
            except core.ParsingFailure:
                if combine:
                    state.parsed = "".join(pieces)
                return state
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
        pieces = deque()
        i = 0
        while state.left != "":
            window = state.left[:window_size]
            if not cond(state, window):
                if i < min_repetitions:
                    raise core.ParsingFailure("Less than requested minimum of repetitions achieved")
                if combine:
                    state.parsed = "".join(pieces)
                return state
            i += 1
        if combine:
            state.parsed = "".join(pieces)
        return state
    return res
