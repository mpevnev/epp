
Parsers module
==============

This module provides actual working parsers, as opposed to service parsers in
the core module. The parsers are split into several categories:

* single-character parsers
* aggregates of single-character parsers
* various

Single-character parsers
========================

All of these fail on empty input.

``alnum``
---------

The signature: ::

        alnum(ascii_only=False)
This function returns a parser that will match any alphanumeric character. If
``ascii_only`` is true, the resulting parser will not accept characters not in
``[a-zA-Z0-9]``.

``alpha``
---------

The signature: ::

        alpha(ascii_only=False)
This function returns a parser that will match any alphabetic character. If
``ascii_only`` is true, the resulting parser will not accept characters not in
``[a-zA-Z]``.

``any_char``
------------

The signature: ::

        any_char()
This function returns a parser that matches any individual character.

``cond_char``
-------------

The signature: ::

        cond_char(condition)
This function returns a parser that will match any character such that
``condition(character)`` is true. Raises ``ValueError`` if ``condition`` is not a 
callable.

``digit``
---------

The signature: ::

        digit()
This function returns a parser that will match a digit in base 10.

``hex_digit``
-------------

The signature: ::

        hex_digit()
This function returns a parser that will match a hexadecimal digit (ignoring
case).

``newline``
-----------

The signature: ::

        newline()
This function returns a parser that will match a newline character (including
Unicode ones).

``nonwhite_char``
-----------------

The signature: ::

        nonwhite_char()
This function returns a parser that will match a single character of anything
but whitespace (newline characters included).

``white_char``

The signature: ::

        white_char(accept_newlines=False)
This function returns a parser that will match a single character of
whitespace, including newlines if ``accept_newlines`` is true.

Aggregates of single-character parsers
======================================

``alnum_word``
--------------

The signature: ::

        alnum_word(ascii_only=False)
This function returns a parser that matches a non-empty sequence of
alphanumeric characters. If ``ascii_only`` is true, the parser will not accept
characters outside ASCII alphanumeric range (``[a-zA-Z0-9]``, if you will).

``alpha_word``
--------------

The signature: ::

        alpha_word(ascii_only=False)
This function returns a parser that matches a non-empty sequence of
alphabetic characters. If ``ascii_only`` is true, the parser will not accept
characters outside ``[a-zA-Z]``.


``any_word``
------------

The signature: ::

        any_word()
This function returns a parser that matches a non-empty sequence of
non-whitespace characters.

``hex_int``
-----------

The signature: ::

        hex_int(must_have_prefix=False)
This function returns a parser that will match an integer in base 16, with or
without ``0x`` prefix. If ``must_have_prefix`` is true, the prefix is mandatory.

``integer``
-----------

The signature: ::

        integer()
This function returns a parser that will match an integer in base 10.

``line``
--------

The signature: ::

        line(include_newline=False)
This function returns a parser that will match a line of text up to the 
terminating newline. If ``include_newline`` is true, the newline character will
be included into the ``parsed`` window.

``whitespace``
--------------

The signature: ::

        whitespace(min_num=1, accept_newlines=False)
This function returns a parser that will match at least ``min_num`` characters of
whitespace, optionally matching newlines as well.

Various
=======

``balanced``
------------

The signature: ::

        balanced(opening_string, closing_string, include_outer_pair=False)
This function returns a parser that matches everything between a balanced pair
of an opening and closing strings. If ``include_outer_pair`` is true, the
parsed string will include outer opening and closing strings, otherwise they
will be excluded.

``end_of_input``
----------------

The signature: ::

        end_of_input()
This function returns a parser that will succeed only if the left input is
empty.

``everything``
--------------

The signature: ::

        everything()
This function returns a parser that will consume all remaining input.

``literal``
-----------

The signature: ::

        literal(lit)
This function returns a parser that will match literal string ``lit``.

``maybe``
---------

The signature: ::

        maybe(parser)
This function returns a parser that will run ``parser`` and return its return
value if it succeeds, otherwise it succeeds without consuming any input.

``many``
--------

The signature: ::

        many(parser, min_hits=0, max_hits=0, combine=True)
This function returns a parser that will match ``parser`` between ``min_hits`` and
``max_hits`` (if either is zero, there is no limit in the corresponding
direction). If ``combine`` is true, combine the ``parsed``s of individual parsing
runs into a single window, otherwise retain the last ``parsed``.

``multi``
---------

The signature: ::

        multi(literals)
This function returns a parser that will match any of the given literals.

``repeat_while``
----------------

The signature: ::

        repeat_while(cond, window_size=1, min_repetitions=0, combine=True)
This function returns a parser that will slice windows of size ``window_size``
from the input and run them through ``cond`` (which should be a callable with
the following signature: (state, window) -> boolean)) until it fails (that is,
returns a falsey value). If min_repetitions is above 0 and less than that many
windows were processed, the parser fails. 

``take``
--------

The signature: ::

        take(num, fail_on_fewer=True)
This function returns a parser that will consume ``num`` characters. If
``fail_on_fewer`` is true, the parser will fail if less than ``num`` characters
are available. Otherwise it'll consume what it can.

``weave``
---------

The signature: ::

        weave(parsers_iterable, separator, trailing=None, stop_on_failure=False)
This function returns a parser that will chain parsers from the iterable,
interspersed by ``separator`` and (unless ``trailing`` is None) terminated by
``trailing``. ``stop_on_failure`` will be sent through to the underlying
``chain``.
