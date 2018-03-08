"""

Extras module.

This module provides some convenience things to use with parsers, mostly data
structures that are useful in effects.

"""


from collections import deque


class SRDeque(deque):
    """
    Self-returning deque.

    Supports all the operations of the normal deques, but returns itself on
    most operations that otherwise return None, making it usable in effects.
    """

    def append(self, elem):
        super().append(elem)
        return self

    def appendleft(self, elem):
        super().append(elem)
        return self

    def clear(self):
        super().clear()
        return self

    def extend(self, iterable):
        super().extend(iterable)
        return self

    def extendleft(self, iterable):
        super().extendleft(iterable)
        return self

    def insert(self, index, elem):
        super().insert(index, elem)
        return self

    def remove(self, elem):
        super().remove(elem)
        return self

    def reverse(self):
        super().reverse()
        return self

    def rotate(self, n=1):
        super().rotate(n)
        return self


class SRDict(dict):
    """
    Self-returning dict.

    Supports all the operations of the normal dicts, but returns itself on
    most operations that otherwise return None, making it usable in effects.

    Also provides 'set' operation which can be used in effects instead of item
    assignment.
    """

    def clear(self):
        super().clear()
        return self

    def update(self, other):
        super().update(other)
        return self

    def set(self, **kwargs):
        """
        Set the given elements of the dict to corresponding values, then return
        itself.
        """
        return self.update(kwargs)


class SRList(list):
    """
    Self-returning list.

    Supports all the operations of the normal lists, but returns itself on most
    operations that otherwise return None, making it usable in effects.

    Also provides 'set' method to use instead of item and slice assigment.
    """

    def append(self, elem):
        super().append(elem)
        return self

    def clear(self):
        super().clear()
        return self

    def extend(self, iterable):
        super().extend(iterable)
        return self

    def insert(self, index, elem):
        super().insert(index, elem)
        return self

    def remove(self, elem):
        super().remove(elem)
        return self

    def reverse(self):
        super().reverse()
        return self

    def sort(self, key=None, reverse=False):
        super().sort(key=key, reverse=reverse)
        return self

    def set(self, index, value):
        """
        Set the element as 'index' to 'value', then return self.

        'index' may also be a slice object, in this case 'value' should be an
        iterable.
        """
        self[index] = value
        return self
