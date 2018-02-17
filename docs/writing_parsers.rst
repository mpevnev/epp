
Writing parsers
===============

So you need a parser that cannot be reasonably expressed in terms of other
parsers. One solution would be to write it by hand. It is quite simple to do.
The only thing you need to do is to write a function that takes a single 
argument, a State object, and returns another State object. This will be your
parser.

State objects are immutable, so you need to create a new one if you want to
modify chain's state. The fields of interest are ``left_start``, ``left_end`` and
``parsed_start`` and ``parsed_end``. When your parser is done, ``left_start`` should
point to the first character among those your parser haven't touched,
``left_end`` should point past the last character that will be included in
future parsings (if, for some reason, you want to restrict input domain in the
middle of parsing). ``parsed_start`` should point to the first character your
parser has affected, and ``parsed_end`` should point past the last character
that was scanned.

To achieve all this, two methods of State class are provided: one is ``_replace``,
which is inherited from named tuples (see Python docs for this one), and the
other is ``consume``, which takes a number of characters as its argument and
returns a new State object where the number of characters were moved from
``left`` window to the ``parsed`` window.

If you want to register an effect in the parser chain, set ``effect`` field to
the desired effect. In this regard, there is a minor thing about ``_replace``: it
treats lack of ``effect`` in its keyword arguments as ``effect=None``, to avoid
accidental duplication of effects. If you want to copy effect from another
parser, you have to do this explicitly.
