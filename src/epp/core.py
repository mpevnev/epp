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
    '_replace' method. !Note!: to avoid duplicating effects accidentally,
    '_replace' treats lack of 'effect' in its arguments as 'effect=None'. So if
    you want to copy an effect from another parser, you have to do it
    explicitly.

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

    __slots__ = []

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
        'parsed' window reset to an empty string. First one gets the effect of
        the original, the second one gets None.
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
        if end.state.effect is not None:
            return end.state.effect(seed, end.state), end.state
        return seed, end.state


#--------- core parsers generators ---------#


def branch(funcs):
    """
    Create a parser that will try given parsers in order and return the state
    of the first successful one.
    """
    def branch_body(state):
        """ A tree of parsers. """
        for parser in funcs:
            try:
                return parser(state)
            except ParsingEnd as end:
                return end.state
            except ParsingFailure:
                continue
        raise ParsingFailure("All parsers in a branching point have failed")
    return branch_body


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
    def catch_body(state):
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
    return catch_body


def chain(funcs, combine=True, stop_on_failure=False, all_or_nothing=True):
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

    If 'all_or_nothing' is truthy (the default), a ParsingEnd exception thrown
    inside it will not cause the effects gathered so far to be registered and
    the part of the string parsed so far to be marked as 'parsed'. If the
    parameter is falsey, partial application of effects and parsers is
    possible. 'all_or_nothing' is suppressed if 'stop_on_failure' is truthy.

    A note on using iterators in chains: if supplied 'funcs' is an iterator,
    there is a possibility of 'funcs' being exausted on the first attempt to
    parse, with subsequent attempts silently succeeding because that's the
    default behaviour for empty 'funcs'. If you want to run your chain several
    times - be it because of lookahead or for different reasons - make sure to
    wrap the iterator in a list or some other reusable iterable (or call
    'reuse_iter' on it, if it comes from a function).
    """
    return _Chain(funcs, combine, stop_on_failure, all_or_nothing)


def effect(eff):
    """
    Register an effect in the chain. The argument should be a callable of two
    arguments with signature
    (value, state) -> value,
    where 'value' is an arbitrary object being constructed by chain's effects,
    and 'state' is the state of the parser chain at the moment of effect's
    registration. Return 'value' can either be a new object, or a modified old
    one.  Alternatively, you can supply the value being modified through a
    nonlocal variable - like
    > values = deque()
    > eff = effect(lambda val, state: values.append(state.parsed)).
    Note that this would tie your effect to the place of invokation and make it
    not particularly reusable.
    """
    def effect_(state):
        """ Register an effect. """
        return state._replace(effect=eff)
    return effect_


def fail():
    """ Return a parser that always fails. """
    def fail_body(state):
        """ Fail immediately. """
        raise ParsingFailure("'fail' parser has been reached")
    return fail_body


def identity():
    """ Return a parser that passes state unchanged. """
    return lambda state: state._replace()


def lazy(generator, *args, **kwargs):
    """
    Make 'generator' lazy. It will only be called when it's time to actually
    parse a string. Useful for recursive parsers.
    """
    def lazy_body(state):
        """ Lazily create a parser. """
        parser = generator(*args, **kwargs)
        return parser(state)
    return lazy_body


def noconsume(parser):
    """ Return a version of 'parser' that doesn't consume input. """
    def noconsume_body(state):
        """ Parse without consuming input. """
        output = parser(state)
        return output._replace(effect=output.effect, left_start=state.left_start)
    return noconsume_body


def stop(discard=False):
    """
    Return a parser that stops parsing immediately.

    If 'discard' is truthy, truncate 'parsed' window, otherwise inherit it from
    the previous parser.
    """
    def stop_body(state):
        """ Stop parsing. """
        if discard:
            state = state._replace(parsed_start=state.left_start,
                                   parsed_end=state.left_start)
        raise ParsingEnd(state._replace())
    return stop_body


def subparse(seed, parser, absorber):
    """
    Create a parser that will run 'parser' (via 'parse') on the current input
    and given seed value, and then register an effect incorporating subchain's
    output value into the main chain using 'absorber', which should be a
    callable:
    (main_chain_value, main_chain_state, parser_value, parser_state) -> value

    Parser's output state will replace chain's state if the operation is
    succesful.

    If parser fails, so does 'subparse'.
    """
    def absorb_inner(state):
        """ Absorb results of another parser into the chain. """
        output = parse(seed, state, parser)
        if output is None:
            raise ParsingFailure("Subparsing failed")
        value, after = output
        after = after._replace(effect=lambda val, st: absorber(val, state, value, after))
        return after
    return absorb_inner


def test(testfn):
    """
    Return a parser that succeeds consuming no input if testfn(state) returns a
    truthy value, and fails otherwise.

    'parsed' window is truncated.
    """
    def test_body(state):
        """ State testing function. """
        if testfn(state):
            return state._replace(parsed_start=state.left_start, parsed_end=state.left_start)
        raise ParsingFailure(f"Function {testfn} returned a falsey value on '{state.left[0:20]}'")
    return test_body


#--------- helper things ---------#


def copy_lookahead(from_parser, to):
    """
    Copy lookahead mode from 'from_parser' to 'to' and return the modified
    parser.
    """
    try:
        to.lookahead = from_parser.lookahead
    except AttributeError:
        pass
    return to


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
        for (s, _) in effect_points:
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


def _restrict(parser, state):
    """
    Return a restricted version of a parser.
    A no-op when used on a parser that performs no lookahead.
    """
    if get_lookahead(parser) is None:
        return parser
    return _RestrictedParser(parser, state)


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


def _partial_parse(state, parser, at):
    """ Parse using only a portion of the input (namely, up to 'at'). """
    use, do_not = state.split(at)
    after = parser(use)
    after = after._replace(effect=after.effect, left_end=do_not.left_end)
    return after


def _try_chain(parsers, from_pos, effect_points):
    """
    Try to parse the state the first parser in the chain remembers.

    Return a tuple (state, index of the first parser to fail).
    In case of failure, 'state' will be None.
    """
    state = parsers[from_pos].state_before
    new_effect_points = deque()
    drop_effects_after = effect_points.find(lambda point: point[1] >= from_pos)
    i = from_pos
    for i in range(from_pos, len(parsers)):
        try:
            parsers[i].state_before = state
            state = parsers[i](state)
            if state.effect is not None:
                new_effect_points.append((state, i))
        except ParsingFailure:
            return (None, i)
        except ParsingEnd as end:
            if drop_effects_after is not None:
                effect_points.drop(len(effect_points) - drop_effects_after)
            effect_points.extend(new_effect_points)
            raise end
    if drop_effects_after is not None:
        effect_points.drop(len(effect_points) - drop_effects_after)
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


class _Chain():
    """
    A chain of parsers.
    """

    def __init__(self, funcs, combine, stop_on_failure, all_or_nothing):
        self.parsers = funcs
        self.combine = combine
        self.stop_on_failure = stop_on_failure
        self.all_or_nothing = all_or_nothing
        self.effect_points = None
        self.first_state = None
        self.lookahead_chain = None

    def __call__(self, state):
        self.reset(state)
        return self.parse()

    def prep_output_state(self, state, early):
        """ Prepare output state: combine 'parsed's and effects. """
        if early and self.all_or_nothing and not self.stop_on_failure:
            return self.first_state
        if self.combine:
            state = state._replace(parsed_start=self.first_state.left_start)
        state = state._replace(effect=_chain_effects(self.effect_points))
        return state

    def prep_end_exception(self, end, state):
        """
        Prepare ParsingEnd exception: attach a prepared output state to it.
        """
        end.state = self.prep_output_state(state, True)
        return end

    def reset(self, state):
        """ Reset the state of the chain. """
        self.effect_points = _CachedAppender()
        self.first_state = state
        self.lookahead_chain = None

    def start_backtracking(self, state, parsers):
        """ Start backtracking, then continue with normal parsing. """
        start_from = len(self.lookahead_chain) - 1
        while True:
            pos = _shift(self.lookahead_chain, start_from)
            if pos is None:
                raise ParsingFailure("No combination of inputs allows successful parsing")
            _reset_chain(self.lookahead_chain, pos)
            after, failed = _try_chain(self.lookahead_chain, pos, self.effect_points)
            if after is None:
                start_from = failed
                continue
            state = after
            try:
                for parser in parsers:
                    state = self.parse_one(state, parser)
                return self.prep_output_state(state, False)
            except ParsingEnd as end:
                raise self.prep_end_exception(end, state)
            except ParsingFailure:
                start_from = len(self.lookahead_chain) - 1
                continue

    def parse(self):
        """ Try to parse the initial state. """
        try:
            parsers = iter(self.parsers)
            state = self.first_state
            for parser in parsers:
                state = self.parse_one(state, parser)
            return self.prep_output_state(state, False)
        except ParsingEnd as end:
            raise self.prep_end_exception(end, state)
        except ParsingFailure as failure:
            if self.stop_on_failure:
                return self.prep_output_state(state, True)
            if self.lookahead_chain is None:
                raise failure
            return self.start_backtracking(state, parsers)

    def parse_one(self, state, parser):
        """ Parse using a single parser. Return the resulting state. """
        pos = None
        if self.lookahead_chain is None and has_lookahead(parser):
            self.lookahead_chain = _CachedAppender()
        if self.lookahead_chain is not None:
            parser = _restrict(parser, state)
            pos = len(self.lookahead_chain)
            self.lookahead_chain.append(parser)
        after = parser(state)
        if after.effect is not None:
            self.effect_points.append((after, pos))
        return after


class _RestrictedParser():
    """ A parser that only operates on a restricted portion of input. """

    def __init__(self, parser, state):
        self.parser = parser
        self.lookahead = get_lookahead(parser)
        self.delta = 0
        self.state_before = state

    def __call__(self, state):
        self.state_before = state
        if self.lookahead is None:
            return self.parser(state)
        if self.lookahead is Lookahead.GREEDY:
            return _partial_parse(state, self.parser, state.left_len - self.delta)
        # is reluctant
        return _partial_parse(state, self.parser, self.delta)

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
