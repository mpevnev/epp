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

    def split(self, at):
        """
        Split the State object in two. Return a tuple with two State objects,
        the first will have 'left' up to, but not including, index 'at', the
        second - starting with 'at' and until the end.
        """
        first = self.copy()
        first.left = self.left[:at]
        second = self.copy()
        second.left = self.left[at:]
        return first, second


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
    parser in the chain raises a ParsingFailure exception.
    """
    def res(state):
        """ A chain of parsers. """
        pieces = deque() if combine else None
        def ifcombine(state):
            """ Concatenate 'parsed's if 'combine' is truthy. """
            if combine:
                state.parsed = "".join(pieces)
            return state
        for parser in funcs:
            pass
        return ifcombine(state)
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


def lazy(generator, *args, **kwargs):
    """
    Make 'generator' lazy. It will only be called when it's time to actually
    parse a string. Useful for recursive parsers.
    """
    def res(state):
        """ Lazily create a parser. """
        parser = generator(*args, **kwargs)
        return parser(state)
    return res


def modify(transformer):
    """
    Return a parser that, when run, modifies chain state.

    Note that 'parsed' of the resulting State object will be overwritten with
    an empty string.
    """
    return lambda state: transformer(state.copy()).set(parsed="")


def noconsume(parser):
    """ Return a version of 'parser' that doesn't consume input. """
    def res(state):
        """ Parse without consuming input. """
        output = parser(state)
        output.left = state.left
        return output
    return res


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


def get_lookahead(parser):
    """
    Return lookahead mode of the parser or None if it doesn't perform lookahead.
    """
    try:
        return parser.lookahead
    except AttributeError:
        return None


def no_lookahead(parser):
    """ Return True if the parser performs no lookahead. """
    return not hasattr(parser, "lookahead")


def has_lookahead(parser):
    """ Return True if the parser has the ability to perform lookahead. """
    return hasattr(parser, "lookahead")


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


#--------- private helper things ---------#


def _chain_reset(parsers, start_at):
    """ Reset all restricted parsers to the right of 'start_at'. """
    length = len(parsers)
    for i in range(start_at + 1, length):
        _reset(parsers[i])


def _overrestricted(parser):
    """ Return True if a parser is maximally restricted. """
    # isinstance may not be idiomatic, but it's safer than relying on parsers
    # not having a particular method.
    if not isinstance(parser, RestrictedParser):
        return True
    return parser.overrestricted()


def _restrict(parser):
    """
    Return a restricted version of a parser.
    A no-op when used on a parser that performs no lookahead.
    """
    if get_lookahead(parser) is None:
        return parser
    return _RestrictedParser(parser)


def _restrict_more(parser):
    """
    Further restrict a parser. A no-op when used on a parser that performs no
    lookahead.
    """
    if not isinstance(parser, RestrictedParser):
        return
    parser.restrict_more()


def _reset(parser):
    """ Reset restrictions on a parser. """
    if not isinstance(parser, RestrictedParser):
        return
    parser.reset()


def _shift(parsers, from_pos):
    """
    Propagate restrictions' change from 'from_pos' to the left end of a parser
    chain.

    Return the index of the last parser affected.
    """
    while from_pos >= 0:
        p = parsers[from_pos]
        _restrict_more(p)
        if _overrestricted(p):
            from_pos -= 1
            continue
        return from_pos
    return 0


def _subparse(state, parser, at):
    """ Parse using only a portion of the input (namely, up to 'at'). """
    use, do_not = state.split(at)
    after = parser(use)
    after.left += do_not.left
    return after


class _CachedAppender():
    """
    A class that tries to combine efficient appending of deques and fast
    indexing of lists.
    """

    def __init__(self):
        self.changed = False
        self.deque = deque()
        self.list = []
        self.empty = True

    def __getitem__(self, index):
        if self.empty:
            raise IndexError("Indexing into an empty appender")
        if self.changed:
            self.update()
        return self.list[index]

    def __iter__(self):
        return iter(self.deque)

    def __setitem__(self, key, value):
        self.deque[key] = value
        self.list[key] = value

    def __len__(self):
        if self.changed:
            self.update()
        return len(self.list)

    def append(self, item):
        """ Add an element to the right side of the underlying deque. """
        self.deque.append(item)
        self.changed = True
        self.empty = False

    def update(self):
        """ Syncronize the underlying list with the deque. """
        self.list = list(self.deque)
        self.changed = False


class _RestrictedParser():
    """ A parser that only operates on a restricted portion of input. """

    def __init__(self, parser):
        self.parser = parser
        self.lookahead = get_lookahead(parser)
        self.delta = 0
        self.last_state = None

    def __call__(self, state):
        if self.lookahead is None:
            res = self.parser(state)
            self.last_state = res
            return res
        if self.lookahead is Lookahead.GREEDY:
            res = _subparse(state, self.parser, len(state.left) - self.delta)
            self.last_state = res
            return res
        # is reluctant
        res = _subparse(state, self.parser, self.delta)
        self.last_state = res
        return res

    def overrestricted(self):
        """
        Return True if restrictions have reached their maximum - that is, if
        either allowed input portion is shrinked into an empty string, or has
        extended beyond the bounds of leftover input.
        """
        return self.delta > len(self.last_state.left)

    def reset(self):
        """ Reset restrictions. """
        self.delta = 0
        self.last_state = None

    def restrict_more(self):
        """ Increase restriction level on the input. """
        self.delta += 1
