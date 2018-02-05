"""

EPP - effectful pythonic parsers, Core module.

The core module provides base classes and some essential parsers.

Parsing functions, or parsers, are just callables that take a State object as
the only argument and return another State object.

If a ParsingFailure exception is thrown by a parser, parsing stops with a
failure.
If a ParsingEnd exception is thrown by a parser, parsing ends prematurely, but
successfully.

"""

from collections import deque, namedtuple
import enum


#--------- base things ---------#


class State(namedtuple("State", "string value left_start left_end parsed_start parsed_end")):
    """
    State objects represent current state of a parser chain (or an individual
    parser).

    State objects provide two views over the input string: 'left', which spans
    a substring between 'left_start' and 'left_end' and represents unparsed
    input left from the previous parser, and 'parsed', which spans a substring
    between 'parsed_start' and 'parsed_end' and represents a portion of input
    the previous parser has parsed. Windows may overlap, and usually
    'parsed_end' and 'left_start' are the same, but not always.

    A State object is immutable and has following fields:
    * string (str): the input the parser chain is supposed to parse.
    * value (anything): an arbitrary object that was created by the parser
      chain. A parser is supposed to create a new value, not modify an old one.
      If you do modify it, you're liable to run into nasty surprises with
      lookahead and branching.
    * left_start, left_end (int): see above about the 'left' window.
    * parsed_start, parser_end (int): see above about the 'parsed' window.

    State objects are just named tuples, so they support a very convenient
    '_replace' method.

    State objects are indexable, indexing into them returns slices or
    characters from the left portion of input and *not* from the whole input.

    State objects' constructor takes the following arguments:
    1. string - the input.
    2. value=None - the value built by a parser chain.
    3. start=0 - will be translated into 'left_start'
    4. end=None - will be translated into 'left_end'. If set to None,
      'left_end' will be set to the length of the input.
    State objects created via this constructor have both 'parsed_start' and 
    'parsed_end' set to zero.

    State objects have several properties:
    * left - returns a slice of input that's left to parse.
    * left_len - returns the length of the above slice without computing the
      slice itself.
    * parsed - returns a slice of input that's been parsed.
    * parsed_len - returns the length of the above slice, again without
      computing the slice.

    Finally, State objects have following public methods:
    * consume(how_many) - move 'how_many' characters from the left window into
      the parsed window. Raise ValueError if more input was consumed than left.
    * split(at) - split the State in two (and return them). The first keeps
      the input up to, but not including, 'at' as its left, the second gets the
      rest. Both have their 'parsed' windows reset to an empty string. Both
      have the same 'value'.
    """

    def __new__(cls, string, value=None, start=0, end=None):
        if end is None:
            end = len(string)
        assert 0 <= start <= end
        return super().__new__(cls, string, value, start, end, 0, 0)

    def __getindex__(self, ix):
        if isinstance(ix, slice):
            start = ix.start
            if start < 0:
                start += self.left_len
            start += self.start
            end = ix.stop
            if end < 0:
                end += self.left_len
            end += self.start
            return self.string[start:ix.step:end]
        if ix < 0:
            ix += self.left_len
        ix += self.start
        return self.string[ix]

    def consume(self, how_many):
        """
        Return a new State object with 'how_many' characters consumed and moved
        to the 'parsed' window.

        Raise ValueError if 'how_many' is negative or if consuming more
        characters than left in the 'left' window.
        """
        if how_many < 0:
            raise ValueError("Negative number of consumed characters")
        left_start = self.left_start + how_many
        parsed_start = self.left_start
        parsed_end = parsed_start + how_many
        if new_start > self.left_end:
            raise ValueError("Consumed more characters than fits in the 'left' window")
        return self._replace(left_start=left_start, parsed_start=parsed_start,
                             parsed_end=parsed_end)

    def split(self, at):
        """
        Split the State in two. The first one keeps a portion of input up to
        'at'th character (exclusive), the second one gets the rest. Both have
        'parsed' window reset to an empty string, and keep the value of the
        original State.
        """
        split_point = self.left_start + at
        first = self._replace(left_end=split_point
                              parsed_start=self.left_start,
                              parsed_end=self.left_start)
        second = self._replace(left_start=split_point,
                               parsed_start=split_point,
                               parsed_end=split_point)
        return first, second

    @property
    def left(self):
        """
        Return the portion of input the last parser hasn't consumed.
        """
        return self.string[self.left_start:self.left_end]

    @property
    def left_len(self):
        """
        Return the length of the portion of input the last parser hasn't
        consumed.
        """
        return self.left_end - self.left_start

    @property
    def parsed(self):
        """
        Return the string parsed by the last parser.
        """
        return self.string[self.parsed_start:self.parsed_end]

    @property
    def parsed_len(self):
        """
        Return the length of the string parsed by the last parser.
        """
        return self.parsed_end - self.parsed_start


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
    Return a parser that will run 'parser' on the current state and absorb the
    resulting state into main chain's state by replacing it with
    > func(main_state, parsers_state).
    """
    def res(state):
        """ Absorb other parser's return value. """
        sub = parser(state)
        return state._replace(value=func(state, sub), start=sub.start, cur=sub.cur)
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
                return parser(state)
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
    wrap the iterator in list or some other *reusable* iterable (or call
    'reuse_iter' on it, if it comes from a function).
    """
    def res(state):
        """ A chain of parsers. """
        lookahead_chain = None
        start = state.start
        def maybe_combine(s):
            """
            Set 'parsed' of the output state to concatenation of parsed
            strings.
            """
            if combine:
                return s._replace(start=start)
            return s
        for parser in funcs:
            if lookahead_chain is None and has_lookahead(parser):
                lookahead_chain = _CachedAppender()
            if lookahead_chain is not None or has_lookahead(parser):
                parser = _restrict(parser)
                lookahead_chain.append(parser)
            try:
                state = parser(state)
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
                    state, failed = _try_chain(lookahead_chain, try_shift, combine)
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
    return lambda state: state


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

    'transformer' should be a callable that takes a State object and returns a
    new State object.

    Note that 'parsed' of the resulting State object will be overwritten with
    an empty string.
    """
    def res(state):
        """ Modify chain's state. """
        out = transformer(state)
        return out._replace(start=state.cur)
    return res


def noconsume(parser):
    """ Return a version of 'parser' that doesn't consume input. """
    def res(state):
        """ Parse without consuming input. """
        output = parser(state)
        return output._replace(start=state.start)
    return res


def stop(discard=False):
    """
    Return a parser that stops parsing immediately.

    Note that the thrown ParsingEnd exception will have the copy of the last
    successful parser's State, unless 'discard' is truthy.

    Also note that using this inside a chain with 'combine=True' will not
    result in previous parsers' chunks concatenated. Their effect on 'left' and
    'value' will persist, though.
    """
    def res(state):
        """ Stop parsing. """
        if discard:
            raise ParsingEnd(state._replace(start=state.cur))
        raise ParsingEnd(state)
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
            return state._replace(start=state.cur)
        raise ParsingFailure(f"Function {testfn} returned a falsey value on "
                             "'{state.string[state.start:20]}'")
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
    res = lambda state: parser(state)
    res.lookahead = Lookahead.RELUCTANT
    return res


def reuse_iter(generator, *args, **kwargs):
    """
    Make an iterable that will call 'generator(*args, **kwargs)' when iterated
    over and use the return value as an iterator.
    """
    class Res():
        """ A reusable iterator container. """
        def __iter__(self):
            return generator(*args, **kwargs)
    return Res()


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
    after = after._replace(end=do_not.end)
    return after


def _try_chain(parsers, from_pos, combine):
    """
    Try to parse the state the first parser in the chain remembers.

    Return a tuple (state, index of the first parser to fail).
    In case of failure, 'state' will be None.
    """
    state = parsers[from_pos].state_before
    start = state.start
    i = from_pos
    for i in range(from_pos, len(parsers)):
        try:
            state = parsers[i](state)
        except ParsingFailure:
            return (None, i)
        except ParsingEnd as end:
            raise end
    if combine:
        state = state._replace(start=start)
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
            return _subparse(state, self.parser, len(state.end) - self.delta)
        # is reluctant
        return _subparse(state, self.parser, self.delta)

    def overrestricted(self):
        """
        Return True if restrictions have reached their maximum - that is, if
        either allowed input portion is shrinked into an empty string, or has
        extended beyond the bounds of leftover input.
        """
        return self.delta > self.state_before.end - self.state_before.start

    def reset(self):
        """ Reset restrictions. """
        self.delta = 0
        self.state_before = None

    def restrict_more(self):
        """ Increase restriction level on the input. """
        self.delta += 1
