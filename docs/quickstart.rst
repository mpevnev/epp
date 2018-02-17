
Quickstart guide
================

The library is written around several concepts. The first concept is State, an
object that holds information about parsing process. Unless you're writing a
parser from scratch, the only thing you should care about is its ``parsed``
property, which holds the string parsed by the last parser. Another concept is
a parser, which is simply a callable that takes a State object as an argument
and returns a new State object. Core module includes some functions that
manipulate parsers. The last key concept is an effect, which is also a
callable, but of two arguments. They will be covered in detail later.

Importing
=========

The module you should import to work with the library is ``epp``. Alternatively,
you can import ``epp.core`` and ``epp.parsers``, but why bother?

Constructing a parser
=====================

Combining basic parsers into more complex ones requires basic parsers. Skim
through parsers module to see what parsers are available.

For parser construction there are two basic tools: ``chain`` and ``branch``. The
former chains an iterable of parsers together, feeding the output of one as 
input to another. The latter chooses between several parsers to find the first
one to succeed on the given input. 

The ``chain``\ s signature is as follows: ::

        chain(parsers, combine=True, stop_on_failure=False, all_or_nothing=True)
``parsers`` is an iterable of parsers to be chained. Note that if you supply an
iterator, there's a possibility of it being exausted on the first try, with
``chain`` silently succeeding consuming no input if it's run again. To avoid
this, wrap 'parsers' into a reusable iterable (say, ``list``), or use
``reuse_iter`` from the core module.

If ``combine`` is true, the chain will consider its ``parsed`` string to contain
all input between first parser's starting point and the last parser's ending
point (note that this *doesn't* mean 'concatenation of individual ``parsed``\ s).
Otherwise, it'll inherit the last parser's ``parsed``.

If ``stop_on_failure`` is true, the chain will stop instead of failing if a
parser inside it fails.

If ``all_or_nothing`` is true, a signal to stop parsing from inside the parser
chain will not cause chain's effects to be collected and ``parsed``\ s to be
joined.  If it is false, partial application of parsers in the chain is
possible.

The ``branch``\ s signature is simpler: ::

        branch(parsers)
``parsers`` is an iterable of parsers. The same note about reusable iterables
applies.

Effects
=======

A parser alone wouldn't do much good. Usually one needs to transform parsed
text into something useful. This is where effects come in. An effect is simply
a callable of two arguments - an arbitrary value, and a State object - which
returns another arbitrary value. A parser may register an effect as it goes
along, and the parsing driver function will later (*iff* the chain is
successful) sequentially apply all registered effects to a seed value as the 
first argument and the State at the moment of effect's registration as the
second: ::

        new_value = current_effect(old_value, effects_state)

While you can write a parser that registers an effect on its own, for most
purposes it's easier to use ``effect`` parser generator (from the core module).
It takes a single argument, which should be the effect to be registered at this
point. Just stick ``effect(whatever)`` into a ``chain`` after a parser which
return state you want to transform into something.

Using all this
==============

Now that you have a parser chain and effects embedded in it, it's time to use
it. To do this, (optionally) wrap a string you want to parse into a 
State object (the argument should be the string. There are more arguments, see
the source if you're interested). Then call ::

        parse(seed, state_or_string, parser).
If the parser managed to parse your string, the function will return a tuple of 
``seed`` after applying the effects and the final State of the chain. If there
has been an error, the function will return None

The end
=======

That's pretty much it. Here's an example of parsing a tuple of integers
separated by whitespace (and there are several more in ``examples`` directory): ::

        string = "1 2"
        parser = epp.chain([epp.integer(),
            epp.effect(lambda val, st: int(st.parsed)),
            epp.integer(),
            epp.effect(lambda val, st: (val, int(st.parsed)))
            ])
        output = epp.parse(None, string, parser)
        value, _ = output
        # value[0] is 1, value[1] is 2
