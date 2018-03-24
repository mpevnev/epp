Extras module
=============

The exstras module provides several utility classes for more convenient usage
of effects. 

Classes
=======

SRDeque
-------

Self-returning deque. Has the same interface as ``collections.deque``, but
returns itself on all operations that otherwise return ``None``, making it
usable in effect lambdas.

SRDict
------

Self-returning dictionary. Has the same interface as usual Python dictionaries,
but returns itself on ``clear`` and ``update`` calls. Also has a ``set`` method
with the following signature: ::

        set(self, **kwargs)
which is equivalent to assigning several entries using usual assignment syntax.


SRList
------

Self-returning list. Has the same interface as normal lists, but returns itself
on most operations that otherwise return ``None``. Also has a ``set`` method
with the following signature: ::

        set(self, index, value)
which is equivalent to ``self[index] = value``, but returns the list after the
assignment.
