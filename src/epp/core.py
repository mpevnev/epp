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

    def __repr__(self):
        return f"State({repr(self.value)}, {repr(self.left[0:40])}, {repr(self.parsed)})"

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
    parser in the chain raises a ParsingFailure exception. Note that this also
    includes parsers with lookahead, effectively disabling it.

    A note on using iterators in chains: if supplied 'funcs' is an iterator,
    there is a possibility of 'funcs' being exausted on the first attempt to
    parse, with subsequent attempts silently succeeding because that's the
    default behaviour for empty 'funcs'. If you want to run your chain several
    times - be it because of lookahead or for different reasons - make sure to
    wrap the iterator in list or some other *reusable* iterable.
    """
    def res(state):
        """ A chain of parsers. """
        pieces = _CachedAppender() if combine else None
        def maybe_combine(state):
            """ Concatenate 'parsed's if 'combine' is truthy. """
            if combine:
                state.parsed = "".join(pieces)
            return state
        lookahead_chain = None
        for parser in funcs:
            if lookahead_chain is None and has_lookahead(parser):
                lookahead_chain = _CachedAppender()
            if lookahead_chain is not None or has_lookahead(parser):
                parser = _restrict(parser)
                lookahead_chain.append(parser)
            try:
                state = parser(state)
                if combine:
                    pieces.append(state.parsed)
            except ParsingEnd as end:
                raise end
            except ParsingFailure as failure:
                if stop_on_failure:
                    return maybe_combine(state)
                if lookahead_chain is None:
                    raise failure
                pos = len(lookahead_chain) - 1
                while True:
                    try_shift = _shift(lookahead_chain, pos)
                    if try_shift is None:
                        raise ParsingFailure(
                            "Failed to find a combination of inputs that allows  "
                            "successful parsing")
                    _reset_chain(lookahead_chain, try_shift)
                    state, failed = _try_chain(lookahead_chain, try_shift, pieces)
                    if state is None:
                        pos = failed
                        continue
                    break
        return maybe_combine(state)
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


def no_lookahead(parser):
    """ Return True if the parser performs no lookahead. """
    return not hasattr(parser, "lookahead")


def reluctant(parser):
    """ Return a reluctant version of 'parser'. """
    try:
        if parser.lookahead is Lookahead.RELUCTANT:
            return parser
    except AttributeError:
        pass
    def res(state):
        retval = parser(state)
        return retval
        return parser(state)
    #res = lambda state: parser(state)
    res.lookahead = Lookahead.RELUCTANT
    return res


#--------- private helper things ---------#


def _overrestricted(parser):
    """ Return True if a parser is maximally restricted. """
    # isinstance may not be idiomatic, but it's safer than relying on parsers
    # not having a particular method.
    if not isinstance(parser, _RestrictedParser):
        return True
    return parser.overrestricted()


def _reset_chain(parsers, start_at):
    """ Reset all restricted parsers to the right of 'start_at'. """
    length = len(parsers)
    for i in range(start_at + 1, length):
        _reset(parsers[i])


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
    if not isinstance(parser, _RestrictedParser):
        return
    parser.restrict_more()


def _reset(parser):
    """ Reset restrictions on a parser. """
    if not isinstance(parser, _RestrictedParser):
        return
    parser.reset()


def _shift(parsers, from_pos):
    """
    Propagate restrictions' change from 'from_pos' to the left end of a parser
    chain.

    Return the index of the last parser affected or None if all restriction
    combinations were tried.
    """
    while from_pos >= 0:
        p = parsers[from_pos]
        _restrict_more(p)
        if _overrestricted(p):
            from_pos -= 1
            continue
        return from_pos
    return None


def _subparse(state, parser, at):
    """ Parse using only a portion of the input (namely, up to 'at'). """
    use, do_not = state.split(at)
    after = parser(use)
    after.left += do_not.left
    return after


def _try_chain(parsers, from_pos, pieces):
    """
    Try to parse the state the first parser in the chain remembers.

    Return a tuple (state, index of the first parser to fail).
    In case of failure, 'state' will be None.

    Also, if 'pieces' is not None, append every parsed chunk to it, having
    first dropped every invalidated piece. If an attempt to parse fails,
    'pieces' will not be affected.
    """
    state = parsers[from_pos].state_before
    i = from_pos
    new_pieces = None if pieces is None else deque()
    for i in range(from_pos, len(parsers)):
        try:
            state = parsers[i](state)
            if pieces is not None:
                new_pieces.append(state.parsed)
        except ParsingFailure:
            return (None, i)
        except ParsingEnd as end:
            raise end
    if pieces is not None:
        # '-1' is here because the last parser does not contribute a piece, as
        # it has failed
        pieces.drop(len(parsers) - from_pos - 1)
        pieces.extend(new_pieces)
    return state, i


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
            return len(self.deque)
        return len(self.list)

    def append(self, item):
        """ Add an element to the right side of the underlying deque. """
        self.deque.append(item)
        self.changed = True
        self.empty = False

    def drop(self, num):
        """
        Remove 'num' elements from the right end of the appender.
        Raise IndexError if 'num' is negative.
        Raise IndexError if 'num' is greater than the size of the appender.
        """
        if num < 0:
            raise IndexError(
                f"Attempted to remove a negative number ({num}) of elements from an appender")
        for _ in range(num):
            try:
                self.deque.pop()
            except IndexError:
                raise IndexError("Attempted to drop more elements than an appender has")
        try:
            _ = self.deque[0]
        except IndexError:
            self.empty = True
        self.changed = True

    def extend(self, iterable):
        """
        Append every item in 'iterable' to the appender.
        """
        for item in iterable:
            self.append(item)
            self.empty = False
            self.changed = True

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
        self.state_before = None

    def __call__(self, state):
        self.state_before = state
        if self.lookahead is None:
            return self.parser(state)
        if self.lookahead is Lookahead.GREEDY:
            return _subparse(state, self.parser, len(state.left) - self.delta)
        # is reluctant
        return _subparse(state, self.parser, self.delta)

    def overrestricted(self):
        """
        Return True if restrictions have reached their maximum - that is, if
        either allowed input portion is shrinked into an empty string, or has
        extended beyond the bounds of leftover input.
        """
        return self.delta > len(self.state_before.left)

    def reset(self):
        """ Reset restrictions. """
        self.delta = 0
        self.state_before = None

    def restrict_more(self):
        """ Increase restriction level on the input. """
        self.delta += 1
