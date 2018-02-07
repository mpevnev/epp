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


class State(namedtuple("State", "string effect left_start left_end parsed_start parsed_end")):
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
    * effect ((value, state) -> value): if the chain is successful, this will
      be called in sequence with other effects from the chain to form the
      chain's output value.
    * left_start, left_end (int): see above about the 'left' window.
    * parsed_start, parser_end (int): see above about the 'parsed' window.

    State objects are just named tuples, so they support a very convenient
    '_replace' method. Note: to avoid duplicating effects accidentally,
    '_replace' treats lack of 'effect' in its arguments as 'effect=None'.

    State objects' constructor takes the following arguments:
    1. string - the input.
    2. effect=None - the effect, transformation to be performed on success of
       the last parser.
    3. start=0 - will be translated into 'left_start'
    4. end=None - will be translated into 'left_end'. If set to None,
      'left_end' will be set to the length of the input.
    State objects created via this constructor have both 'parsed_start' and
    'parsed_end' set to 'left_start'.

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
      the input up to, but not including, 'at' as its 'left' window, the second
      gets the rest. Both have their 'parsed' windows reset to an empty string.
      The first gets 'effect' of the original, the second gets None.
    """

    def __new__(cls, string, effect=None, start=0, end=None):
        if end is None:
            end = len(string)
        assert 0 <= start <= end <= len(string)
        return super().__new__(cls, string, effect, start, end, start, start)

    def _replace(self, **kwargs):
        if "effect" not in kwargs:
            return super()._replace(effect=None, **kwargs)
        return super()._replace(**kwargs)

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
        if left_start > self.left_end:
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
        first = self._replace(effect=self.effect,
                              left_end=split_point,
                              parsed_start=self.left_start,
                              parsed_end=self.left_start)
        second = self._replace(effect=None,
                               left_start=split_point,
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


def parse(seed, state_or_string, parser, verbose=False):
    """
    Run a given parser on a given state object or a string, then apply combined
    chain or parser's effects to 'seed' and return a tuple 
    (seed after effects, final state).

    On failure, return None unless 'verbose' is truthy, in which case return
    the ParsingFailure exception that has terminated the parsing process.
    """
    if isinstance(state_or_string, str):
        state = State(state_or_string)
    else:
        state = state_or_string
    try:
        after = parser(state)
        if after.effect is not None:
            return after.effect(seed, after), after
        return seed, after
    except ParsingFailure as failure:
        if verbose:
            return failure
        return None
    except ParsingEnd as end:
        if end.effect is not None:
            return end.state.effect(seed, end.state), end.state
        return seed, end.state


#--------- core parsers generators ---------#


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
        raise ParsingFailure("All parsers in a branching point have failed")
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

    If 'combine' is truthy, resulting 'parsed' window will cover the input
    between starting point of the first parser and the ending point of the
    last one. Note that this might be different than what you'd get by
    concatenating together individual 'parsed' windows if some of the parsers
    performed unusual operations on their windows - like 'noconsume' does, for
    example.

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

    Note that chains are all-or-nothing constructs - if a chain is terminated
    in any way - by ParsingFailure or ParsingEnd or any other exception - the
    effects of the part of the chain that was applied will not be saved.
    """
    def res(state):
        """ A chain of parsers. """
        lookahead_chain = None
        start = state.left_start
        effect_points = _CachedAppender()
        def prep_output(s):
            """
            Combine effects and (if 'combine' is truthy) 'parsed' windows.
            """
            if combine:
                s = s._replace(parsed_start=start)
            return s._replace(effect=_chain_effects(effect_points))
        for parser in funcs:
            if lookahead_chain is None and has_lookahead(parser):
                lookahead_chain = _CachedAppender()
            if lookahead_chain is not None or has_lookahead(parser):
                parser = _restrict(parser)
                lookahead_chain.append(parser)
            try:
                state = parser(state)
                if state.effect is not None:
                    effect_points.append(state)
            except ParsingEnd as end:
                raise end
            except ParsingFailure as failure:
                if stop_on_failure:
                    return prep_output(state)
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
                    state, failed = _try_chain(lookahead_chain, try_shift, effect_points)
                    if state is None:
                        pos = failed
                        continue
                    break
        return prep_output(state)
    return res


def effect(eff):
    """
    Register an effect in the chain. The argument should be a callable of two
    arguments: the first is the value being built by effects, the second is the
    remembered state of the parser chain.
    """
    def effect_(state):
        """ Register an effect. """
        return state._replace(effect=eff)
    return effect_


def fail():
    """ Return a parser that always fails. """
    def res(state):
        """ Fail immediately. """
        raise ParsingFailure("'fail' parser has been reached")
    return res


def identity():
    """ Return a parser that passes state unchanged. """
    return lambda state: state._replace()


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


def noconsume(parser):
    """ Return a version of 'parser' that doesn't consume input. """
    def res(state):
        """ Parse without consuming input. """
        output = parser(state)
        return output._replace(left_start=state.left_start)
    return res


def stop(discard=False):
    """
    Return a parser that stops parsing immediately.

    If 'discard' is truthy, truncate 'parsed' window, otherwise inherit it from
    the previous parser.

    Also note that using this inside a chain with 'combine=True' will not
    result in previous parsers' chunks concatenated. Their effect on 'left' and
    'value' will persist, though.
    """
    def res(state):
        """ Stop parsing. """
        if discard:
            state = state._replace(parsed_start=state.left_start,
                                   parsed_end=state.left_start)
            raise ParsingEnd(state)
        raise ParsingEnd(state)
    return res


def test(testfn):
    """
    Return a parser that succeeds consuming no input if testfn(state) returns a
    truthy value, and fails otherwise.

    'parsed' window is truncated.
    """
    def res(state):
        """ State testing function. """
        if testfn(state):
            return state._replace(parsed_start=state.left_start, parsed_end=state.left_start)
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


def _chain_effects(effect_points):
    """ Chain effects saved in 'states' together into a single effect. """
    def chained_effects(value, state):
        """ A chain of effects. """
        for s in effect_points:
            value = s.effect(value, s)
        return value
    return chained_effects


def _overrestricted(parser):
    """ Return True if a parser is maximally restricted. """
    # isinstance may not be idiomatic, but it's safer than relying on parsers
    # not having a particular method.
    if not isinstance(parser, _RestrictedParser):
        return True
    return parser.overrestricted()


def _reset(parser):
    """ Reset restrictions on a parser. """
    if not isinstance(parser, _RestrictedParser):
        return
    parser.reset()


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
    after = after._replace(left_end=do_not.left_end)
    return after


def _try_chain(parsers, from_pos, effect_points):
    """
    Try to parse the state the first parser in the chain remembers.

    Return a tuple (state, index of the first parser to fail).
    In case of failure, 'state' will be None.
    """
    state = parsers[from_pos].state_before
    new_effect_points = deque()
    drop_effects_after = effect_points.find(lambda point: point is state)
    i = from_pos
    for i in range(from_pos, len(parsers)):
        try:
            state = parsers[i](state)
            if state.effect is not None:
                new_effect_points.append(state)
        except ParsingFailure:
            return (None, i)
        except ParsingEnd as end:
            raise end
    if drop_effects_after is not None:
        effect_points.drop(len(effect_points) - (drop_effects_after + 1))
    effect_points.extend(new_effect_points)
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
        """ Drop 'num' elements from the right end. """
        for _ in range(num):
            self.deque.pop()
            self.changed = True
        try:
            _ = self.deque[0]
        except IndexError:
            self.empty = True

    def extend(self, iterable):
        """ Append all elements of an iterable. """
        for item in iterable:
            self.deque.append(item)
            self.changed = True
            self.empty = False

    def find(self, pred):
        """
        Return the index of an element such that 'pred(element)' returns True
        or None if no such element was found.
        """
        self.update()
        for i, val in enumerate(self.deque):
            if pred(val):
                return i
        return None

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
            return _subparse(state, self.parser, len(state.left_end) - self.delta)
        # is reluctant
        return _subparse(state, self.parser, self.delta)

    def overrestricted(self):
        """
        Return True if restrictions have reached their maximum - that is, if
        either allowed input portion is shrinked into an empty string, or has
        extended beyond the bounds of leftover input.
        """
        return self.delta > self.state_before.left_end - self.state_before.left_start

    def reset(self):
        """ Reset restrictions. """
        self.delta = 0
        self.state_before = None

    def restrict_more(self):
        """ Increase restriction level on the input. """
        self.delta += 1
