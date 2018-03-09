
Core module
===========

The core module provides base classes that parsers use as well as several
essential parser generators.

Base classes
============

Following classes are defined in the core module: ``State``, ``ParsingFailure``,
``ParsingEnd``, ``Lookahead``. Their descriptions (short, for the long ones see 
respective docstrings in the code) and roles are given below.

Parser driver
-------------

The main control function for parsing is ``parse``. It has the following
signature: ::
        parse(seed, state_or_string, parser, verbose=False)

It will run ``parser`` on the given State object or a string, collect effects
registered during parser's run, and if parsing is successful, apply collected
effects to ``seed``. On success it will return a tuple with seed after
transformations introduced by the effects and with the state after the last
parser was done. On failure it will either return None (if ``verbose`` is false),
or the ``ParsingFailure`` exception that has terminated the chain.

``State``
---------

State objects represent current state of a parser chain. They are a subclass of
named tuples (and therefore immutable). State objects maintain two windows over
the input string: a ``parsed`` window (given via ``parsed_start`` and ``parsed_end``
indices), which contains the part of the input consumed by the last parser, and
``left`` window, (given by ``left_start`` and ``left_end`` indices), which contains
the part of the input that wasn't parsed yet. Being named tuples, State objects
support ``_replace`` method. Another useful method is ``consume(num)``, which
returns a new State object with ``num`` characters consumed (i.e. moved from
``left`` window to ``parsed`` window).

``ParsingFailure``
------------------

An exception of this type should be raised if a parser can't parse its input.
The constructor has the following signature: ::

        __init__(self, failed_state, text, code=0)
Here ``failed_state`` should be the state that caused the parser to fail, 
``text`` should be an error message and ``code`` should represent the exact
reason for failure (for codes for built-in parsers see file ``errors.py``)

``ParsingEnd``
--------------

An exception of this type should be raised if there's a need to stop parsing
immediately, but not fail it. Exact behaviour of this type of signals is 
described in ``chain``\ s docstring.

``Lookahead``
-------------

An enum type which contains lookahead modes, namely ``GREEDY`` and ``RELUCTANT``.
Most likely you don't need to know about its existence.

Parser generators
=================

The core module defines several parser generators. They differ from those in
the parsers module in that they don't really parse anything, they are service
functions.

``branch``
----------

The signature: ::

        branch(iterable_of_parsers, save_iterator=True)
This function returns a parser that will try each of parsers in the iterable in
order and return the state of the first successful one.

If ``save_iterator`` is true, the parsers in the supplied iterator will be
saved, allowing to safely reuse the resulting parser - otherwise there is a 
danger of the iterator being consumed on the first run, leaving nothing for
future runs. This, however, leads to higher memory consumption, and is
unnecessary if you already use a reusable iterable such as a list or a deque.
You can disable saving by passing False as this parameter.

``catch``
---------

The signature: ::

        catch(parser, exception_types, on_thrown=None, on_not_thrown=None)
This function returns a parser that will run ``parser`` and see if it has raised
an exception. If an exception of any type given by ``exception_types`` is raised,
``on_thrown`` is called (unless it's None):
``on_thrown(state_before_parser, caught_exception)``
and its return value (which should be a State object) is used as the return
value of the parser. If no exception of any specified type was raised, 
``on_not_thrown`` is called (again, unless it's None):
``on_not_thrown(inner_parsers_state)``
and its return value is used as the return value of the parser.

Note that ``ParsingFailure`` and ``ParsingEnd`` cannot be caught in this manner.

``chain``
---------

The signature: ::

        chain(parsers, combine=True, stop_on_failure=False, all_or_nothing=True, save_iterator=True)
This function returns a parser that will run parsers in the ``parsers`` iterable
feeding output of one as input to the next. For complete breakdown of
parameters meaning, see the docstring on this function. 

``effect``
----------

The signature: ::

        effect(eff)
This function returns a parser that will register an effect when it's run.
``eff`` should be a callable:
``(value, state) -> new_value``.
``value`` can be an arbitrary object received from the previous effect (or from
the seed), ``state`` is the State object at the moment of effect's registration.
``new_value`` doesn't necessarily have to be meaningful: ::

        arr = [1, 2, 3]
        parser = effect(lambda val, st: val.append(5))
is perfectly legal and will work as expected.

``fail``
--------

The signature: ::

        fail()
This function returns a parser that always fails without consuming any input.

``identity``
-----------

The signature: ::

        identity()
This function returns a parser that passes its State unchanged (but does erase
the effect from it, to avoid accidental effect duplication).

``lazy``
--------

The signature: ::

        lazy(generator, *args, **kwargs)
This function returns a parser that, when run, will call ``generator`` with
``args`` and ``kwargs`` as its argumentss and then will run its return value as a 
parser. This is primarily intended to be used in recursive parsers.


``modify_error``
----------------

The signature: ::

        modify_error(parser, error_transformer)
This function wraps ``parser`` into a new parser that will transform any
``ParsingFailure`` exception thrown inside the underlying parser. 
``error_transformer`` should be a callable with a single argument, which will
be the raised exception, and should return either a modified exception or a new
one. Useful if you wish to change the error message to a more descriptive one.

``noconsume``
-------------

The signature: ::

        noconsume(parser)
This function returns a parser that behaves exactly like ``parser``, but consumes
no input.

``stop``
--------

The signature: ::

        stop(discard=False)
This function returns a parser that will stop parser chain's execution
immediately, but successfully. If ``discard`` is true, the ``parsed`` window will
be truncated, otherwise it will be inherited from the previous parser.

``subparse``
------------

The signature: ::

        subparse(seed, parser, absorber)
This function returns a parser that will run ``parser`` on the current input,
apply its effects to ``seed``, and then absorb (as an effect) its return value by
calling ::

        absorber(main_chain_value, main_chain_state, subchain_value, subchain_state)
and replacing main chain's return value with absorber's.

``test``
--------

The signature: ::

        test(testfn)
This function returns a parser that will call ``testfn`` on the State it's given
and fails if ``testfn`` returns false, otherwise it succeeds consuming no input.

Lookahead utilities
===================

Normally, parsers gobble up as much input as they can, not caring about what
the following parsers have to work with. This can be changed by marking parsers
as having lookahead capabilities. This is done via the following two functions
(also usable as decorators): ``greedy`` and ``reluctant``. A greedy parser will
start parsing with as much input as it can, surrendering portions of it if the 
following parsers do not succeed. A reluctant parser will start with as little
input as it can, adding more input to its allowed portion if needed for the 
following parsers to succeed. Alternatively, you can mark a parser as having
lookahead by setting ``lookahead`` attribute on it to either ``Lookahead.GREEDY``
or ``Lookahead.RELUCTANT``.
