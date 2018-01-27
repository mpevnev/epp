"""

EPP - effectful pythonic parsers, Core module.

The core module provides base classes and some essential parsers.

Parsing functions, or parsers, are just callables that take a State object as
the only argument and return another State object. Note that they should return
a *new* State object, not modify an old one, as this will lead to nasty issues
in lookahead and branch selection.

If a ParsingFailure exception is thrown by a parser, parsing stops with a
failure.
If a ParsingEnd exception is thrown by a parser, parsing ends prematurely, but
successfully.

"""

from collections import deque
from copy import deepcopy
import enum

#--------- base things ---------#


class State():
    """ An object representing current parser state. """

    def __init__(self, left, value=None, parsed=""):
        self.value = value
        self.left = left
        self.parsed = parsed

    def __eq__(self, other):
        return (self.value == other.value and
                self.left == other.left and
                self.parsed == other.parsed)

    def copy(self):
        """ Shallow copy the State object. """
        return State(self.left, self.value, self.parsed)

    def deepcopy(self):
        """ Deep copy the State object. """
        return deepcopy(self)

    def set(self, **kwargs):
        """ Return a new State object with given attributes. """
        left = kwargs.get("left", self.left)
        value = kwargs.get("value", self.value)
        parsed = kwargs.get("parsed", self.parsed)
        return State(left, value, parsed)

    def consume(self, how_many):
        """ Return a new State object with 'how_many' characters consumed. """
        return State(self.left[how_many:], self.value, self.left[0:how_many])

    def blank(self):
        """
        Return a new State object with the same 'left' but with None 'parsed'
        value.
        """
        return State(self.left)


class ParsingFailure(Exception):
    """ An exception of this type should be thrown if parsing fails. """
    pass


class ParsingEnd(Exception):
    """
    An exception of this type should be thrown if parsing ends successfully,
    but early.
    """

    def __init__(self, state):
        super().__init__()
        self.state = state


class Lookahead(enum.Enum):
    """ Lookahead type. """
    GREEDY = enum.auto()
    RELUCTANT = enum.auto()


def parse(state_or_string, parser, verbose=False):
    """
    Run a given parser on a given state object or a string.
    Return parser's return value on success, or None on failure.

    If 'verbose' is truthy, return terminating ParsingFailure exception on
    failure instead of None.
    """
    if isinstance(state_or_string, str):
        state = State(state_or_string)
    else:
        state = state_or_string
    try:
        return parser(state)
    except ParsingFailure as failure:
        if verbose:
            return failure
        return None
    except ParsingEnd as end:
        return end.state


#--------- core parsers generators ---------#


def absorb(func, parser):
    """
    Return a parser that will run 'parser' on a 'blank'ed state and absorb the
    result into of the current chain by replacing current chain's state with
    > func(state, parsers_output).

    'parsed' is filled with an empty string.
    'left' is inherited from 'parser's output.
    """
    def res(state):
        """ Absorb other parser's return value. """
        parsers_output = parser(state.blank())
        return func(state, parsers_output).set(parsed="", left=parsers_output.left)
    return res


def branch(funcs):
    """
    Create a parser that will try given parsers in order and return the state
    of the first successful one.
    """
    def res(state):
        """ A tree of parsers. """
        for parser in funcs:
            try:
                return parser(state.copy())
            except ParsingEnd as end:
                return end.state
            except ParsingFailure:
                continue
        raise ParsingFailure("All the parsers in a branching point failed")
    return res


def catch(parser, exception_types, on_thrown=None, on_not_thrown=None):
    """
    Return a parser that runs 'parser' and catches exceptions of any of types
    given by 'exception_types'.

    If any exception was caught, 'on_thrown' is called as follows:
    > on_thrown(original_state, caught_exception)
    and its return value (which should be a State object) replaces the original
    parser chain's state.

    If no exception was caught, 'on_not_thrown' is called:
    > on_not_thrown(parsers_state)
    and its return value replaces parser chain's state.

    Both 'on_thrown' and 'on_not_thrown' may be None, in this case no action is
    performed.

    Note that ParsingFailure and ParsingEnd exceptions are exempt from being
    caught in this manner.
    """
    exception_types = tuple(exception_types)
    def res(state):
        """ Try to catch an exception thrown by another parser. """
        try:
            if on_not_thrown is None:
                return parser(state)
            return on_not_thrown(parser(state))
        except ParsingFailure as failure:
            raise failure
        except ParsingEnd as end:
            raise end
        except Exception as exc:
            if isinstance(exc, exception_types):
                if on_thrown is not None:
                    return on_thrown(state, exc)
                return state
            raise exc
    return res


def chain(funcs, combine=True, stop_on_failure=False):
    """
    Create a parser that chains a given iterable of parsers together, using
    output of one parser as input for another.

    If 'combine' is truthy, combine 'parsed's of the parsers in the chain,
    otherwise use the last one.

    If 'stop_on_failure' is truthy, stop parsing instead of failing it when a
    parser in the chain raises a ParsingFailure exception. This should be used
    with extreme caution if several layers of nested parsers are used, as the
    end result may not be what you expect.
    """
    def res(state):
        """ A chain of parsers. """
        pieces = deque() if combine else None
        for parser in funcs:
            try:
                state = parser(state)
                if combine:
                    pieces.append(state.parsed)
            except ParsingEnd as end:
                if combine:
                    end.state.parsed = "".join(pieces)
                return end.state
            except ParsingFailure as failure:
                if stop_on_failure:
                    if combine:
                        state.parsed = "".join(pieces)
                    return state
                raise failure
        if combine:
            state.parsed = "".join(pieces)
        return state
    return res


def fail():
    """ Return a parser that always fails. """
    def res(state):
        """ Fail immediately. """
        raise ParsingFailure("'fail' parser has been reached")
    return res


def identity():
    """ Return a parser that passes state unchanged. """
    return lambda state: state.copy()


def modify(transformer):
    """
    Return a parser that, when run, modifies chain state.

    Note that 'parsed' of the resulting State object will be overwritten with
    an empty string.
    """
    return lambda state: transformer(state.copy()).set(parsed="")


def stop(discard=False):
    """
    Return a parser that stops parsing immediately.

    Note that the thrown ParsingEnd exception will have the copy of the last
    successful parser's State, unless 'discard' is truthy.
    """
    def res(state):
        """ Stop parsing. """
        if discard:
            raise ParsingEnd(state.set(parsed=""))
        raise ParsingEnd(state.copy())
    return res


def test(testfn):
    """
    Return a parser that succeeds consuming no input if testfn(state) returns a
    truthy value, and fails otherwise.

    'parsed' is reset to an empty string.
    """
    def res(state):
        """ State testing function. """
        if testfn(state):
            return state.set(parsed="")
        raise ParsingFailure(f"Function {testfn} returned a falsey value on '{state.left[0:20]}'")
    return res


#--------- helper things ---------#


def no_lookahead(parser):
    """ Return True if the parser performs no lookahead. """
    return not hasattr(parser, "lookahead")


def is_greedy(parser):
    """ Return True if the parser is greedy, False otherwise. """
    try:
        return parser.lookahead is Lookahead.GREEDY
    except AttributeError:
        return False


def is_reluctant(parser):
    """ Return True if the parser is reluctant, False otherwise. """
    try:
        return parser.lookahead is Lookahead.RELUCTANT
    except AttributeError:
        return False


def greedy(parser):
    """ Return a greedy version of 'parser'. """
    try:
        if parser.lookahead is Lookahead.GREEDY:
            return parser
    except AttributeError:
        pass
    res = lambda state: parser(state)
    res.lookahead = Lookahead.GREEDY
    return res


def reluctant(parser):
    """ Return a reluctant version of 'parser'. """
    try:
        if parser.lookahead is Lookahead.RELUCTANT:
            return parser
    except AttributeError:
        pass
    res = lambda state: parser(state)
    res.lookahead = Lookahead.RELUCTANT
    return res
