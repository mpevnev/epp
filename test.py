#!/usr/bin/python

"""
Unit tests for epp library.
"""

import unittest

import epp.core as core
import epp.parsers as par


class TestCore(unittest.TestCase):
    """ Test core parsers and functions. """

    def test_absorb(self):
        """ Test 'absorb' parser generator. """
        string = "12"
        state = core.State(string, {})
        absorbee = core.chain([
            par.literal("12"),
            core.modify(lambda state: state.set(value=int(state.parsed)))])
        def absorber(state, to_be_absorbed):
            """ A function which will absorb a parsed integer into main state. """
            state = state.deepcopy()
            state.value["key"] = to_be_absorbed.value
            return state
        parser = core.absorb(absorber, absorbee)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, {"key": 12})
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, "")

    def test_branch_negative_1(self):
        """ Test 'branch' parser generator, negative check #1. """
        string = "4"
        state = core.State(string)
        parser = core.branch([
            par.literal("1"),
            par.literal("2"),
            par.literal("3")])
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, "4")
        self.assertEqual(state.parsed, "")

    def test_branch_positive_1(self):
        """ Test 'branch' parser generator, positive check #1. """
        string = "21"
        state = core.State(string)
        parser = core.branch([
            par.literal("1"),
            par.literal("2"),
            par.literal("3")])
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIs(state_after.value, None)
        self.assertEqual(state_after.parsed, "2")
        self.assertEqual(state_after.left, "1")

    def test_branch_positive_2(self):
        """ Test 'branch' parser generator, positive check #2. """
        # AKA 'order matters'.
        string = "ab3"
        state = core.State(string)
        parser = core.branch([
            par.literal("ab"),
            par.literal("a")])
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIs(state_after.value, None)
        self.assertEqual(state_after.parsed, "ab")
        self.assertEqual(state_after.left, "3")

    def test_catch_negative_1(self):
        """ Test 'catch' parser generator, negative check #1. """
        def inner_parser(state):
            """ A silly parser that only throws exceptions. """
            raise ValueError
        parser = core.catch(inner_parser, [TypeError])
        string = "foobar"
        with self.assertRaises(ValueError):
            core.parse(string, parser)

    def test_catch_positive_1(self):
        """ Test 'catch' parser generator, positive check #1. """
        def inner_parser(state):
            """ A silly parser that only thrown exceptions. """
            raise ValueError
        def on_thrown(state, exception):
            """ Exception handler. """
            return state.set(value=state.value + 10)
        string = "12"
        state = core.State(string, value=0)
        parser = core.catch(inner_parser, [ValueError], on_thrown, None)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 10)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, string)

    def test_catch_positive_2(self):
        """ Test 'catch' parser generator, positive check #2. """
        def on_not_thrown(state):
            """ Unexception handler. """
            return state.set(value=state.value + 10)
        string = "12"
        state = core.State(string, value=0)
        parser = core.catch(core.identity(), [Exception], None, on_not_thrown)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 10)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, string)

    def test_chain_negative_1(self):
        """ Test 'chain' parser generator, negative check #1. """
        string = "123"
        state = core.State(string)
        parser = core.chain([
            par.literal("!"),
            par.literal("2"),
            par.literal("3")])
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "123")

    def test_chain_negative_2(self):
        """ Test 'chain' parser generator, negative check #2. """
        string = "1x3"
        state = core.State(string)
        parser = core.chain([
            par.literal("1"),
            par.literal("2"),
            par.literal("3")])
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "1x3")

    def test_chain_positive_1(self):
        """ Test 'chain' parser generator, positive check #1. """
        string = "123"
        state = core.State(string)
        parser = core.chain(
            [
                par.literal("1"),
                par.literal("2"),
                par.literal("3")
            ],
            combine=False)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "3")
        self.assertEqual(state_after.left, "")

    def test_chain_positive_2(self):
        """ Test 'chain' parser generator, positive check #2. """
        string = "123"
        state = core.State(string)
        parser = core.chain(
            [
                par.literal("1"),
                par.literal("2"),
                par.literal("3")
            ],
            combine=True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_fail(self):
        """ Test 'fail' parser generator. """
        string = "irrelevant"
        state = core.State(string)
        parser = core.fail()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)

    def test_identity(self):
        """ Test 'identity' parser generator. """
        string = "foobar"
        state = core.State(string)
        parser = core.identity()
        state_after = core.parse(state, parser)
        self.assertEqual(state_after, state)

    def test_modify(self):
        """ Test 'modify' parser generator. """
        string = "doesn't change"
        state = core.State(string, 0)
        parser = core.modify(lambda state: state.set(value=state.value + 10))
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 10)
        self.assertEqual(state_after.left, string)
        self.assertEqual(state_after.parsed, "")

    def test_stop(self):
        """ Test 'stop' parser generator. """
        string = "123"
        state = core.State(string)
        chain = core.chain(
            [
                par.literal("1"),
                par.literal("2"),
                core.stop(),
                par.literal("3")
            ],
            combine=True)
        state_after = core.parse(state, chain)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "3")
        self.assertEqual(state_after.parsed, "12")

    def test_test_negative_1(self):
        """  Test 'test' parser generator, negative check #1. """
        test = lambda state: int(state.parsed) > 10
        string = "6"
        state = core.State(string)
        parser = core.chain([
            par.literal("6"),
            core.test(test)])
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "6")

    def test_test_positive_1(self):
        """ Test 'test' parser generator, positive check #1. """
        test = lambda state: int(state.parsed) > 10
        string = "12"
        state = core.State(string)
        parser = core.chain(
            [
                par.literal("12"),
                core.test(test)
            ],
            combine=True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.parsed, "12")
        self.assertEqual(state_after.left, "")
        self.assertIsNone(state_after.value)


class TestParsers(unittest.TestCase):
    """ Test concrete parsers. """

    #--------- single-character parsers ---------#

    def test_alnum_negative_1(self):
        """ Test 'alnum' parser generator, negative check #1. """
        string = ""
        state = core.State(string)
        parser = par.alnum()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, "")
        self.assertEqual(state.parsed, "")

    def test_alnum_negative_2(self):
        """ Test 'alnum' parser generator, negative check #2. """
        string = '_'
        state = core.State(string)
        parser = par.alnum(False)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_alnum_negative_3(self):
        """ Test 'alnum' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = core.State(string)
        parser = par.alnum(True)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_alnum_positive_1(self):
        """ Test 'alnum' parser generator, positive check #1. """
        string = "1a"
        state = core.State(string)
        parser = core.chain([par.alnum(), par.alnum()], True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_alnum_positive_2(self):
        """ Test 'alnum' parser generator, positive check #2. """
        string = "\U000000DF" # Eszet
        state = core.State(string)
        parser = par.alnum(False)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_alpha_negative_1(self):
        """ Test 'alpha' parser generator, negative check #1. """
        state = core.State("")
        parser = par.alpha()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "")

    def test_alpha_negative_2(self):
        """ Test 'alpha' parser generator, negative check #2. """
        string = "1"
        state = core.State(string)
        parser = par.alpha()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_alpha_negative_3(self):
        """ Test 'alpha' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = core.State(string)
        parser = par.alpha(True)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_alpha_positive_1(self):
        """ Test 'alpha' parser generator, positive check #1. """
        string = "ab"
        state = core.State(string)
        parser = par.alpha(True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "a")
        self.assertEqual(state_after.left, "b")

    def test_alpha_positive_2(self):
        """ Test 'alpha' parser generator, positive check #2. """
        string = "\U000000DFb"
        state = core.State(string)
        parser = par.alpha(False)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "\U000000DF")
        self.assertEqual(state_after.left, "b")

    def test_digit_negative_1(self):
        """ Test 'digit' parser generator, negative check #1. """
        string = ""
        state = core.State(string)
        parser = par.digit()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "")

    def test_digit_negative_2(self):
        """ Test 'digit' parser generator, negative check #2. """
        string = "a"
        state = core.State(string)
        parser = par.digit()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_digit_positive_1(self):
        """ Test 'digit' parser generator, positive check #1. """
        string = "1a"
        state = core.State(string)
        parser = par.digit()
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "1")
        self.assertEqual(state_after.left, "a")

    def test_newline_negative_1(self):
        """ Test 'newline' parser generator, negative check #1. """
        string = ""
        state = core.State(string)
        parser = par.newline()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.parsed, "")
        self.assertEqual(state.left, "")

    def test_newline_negative_2(self):
        """ Test 'newline' parser generator, negative check #2. """
        string = "a"
        state = core.State(string)
        parser = par.newline()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_newline_positive_1(self):
        """ Test 'newline' parser generator, positive check #1. """
        string = "\nb"
        state = core.State(string)
        parser = par.newline()
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "\n")
        self.assertEqual(state_after.left, "b")

    def test_nonwhite_char_negative_1(self):
        """ Test 'nonwhite_char' parser generator, negative check #1. """
        string = ""
        state = core.State(string)
        parser = par.nonwhite_char()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_nonwhite_char_negative_2(self):
        """ Test 'nonwhite_char' parser generator, negative check #2. """
        string = " "
        state = core.State(string)
        parser = par.nonwhite_char()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_nonwhite_char_positive_1(self):
        """ Test 'nonwhite_char' parser generator, positive check #1. """
        string = "b"
        state = core.State(string)
        parser = par.nonwhite_char()
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_white_char_negative_1(self):
        """ Test 'white_char' parser generator, negative check #1. """
        string = "b"
        state = core.State(string)
        parser = par.white_char()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_white_char_negative_2(self):
        """ Test 'white_char' parser generator, negative check #2. """
        string = "\n"
        state = core.State(string)
        parser = par.white_char(False)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_white_char_negative_3(self):
        """ Test 'white_char' parser generator, negative check #3. """
        string = ""
        state = core.State(string)
        parser = par.white_char()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_white_char_positive_1(self):
        """ Test 'white_char' parser generator, positive check #1. """
        string = " b"
        state = core.State(string)
        parser = par.white_char()
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, " ")

    def test_white_char_positive_2(self):
        """ Test 'white_char' parser generator, positive check #2. """
        string = "\nb"
        state = core.State(string)
        parser = par.white_char(True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, "\n")

    #--------- aggregates and variations of the above ---------#

    def test_integer_negative_1(self):
        """ Test 'integer' parser generator, negative check #1. """
        string = "foobar"
        state = core.State(string)
        parser = par.integer()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_integer_negative_2(self):
        """ Test 'integer' parser generator, negative check #2. """
        string = ""
        state = core.State(string)
        parser = par.integer()
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_integer_positive_1(self):
        """ Test 'integer' parser generator, positive check #1. """
        string = "123foo"
        state = core.State(string)
        parser = par.integer(False)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "foo")
        self.assertEqual(state_after.parsed, "123")

    def test_integer_positive_2(self):
        """ Test 'integer' parser generator, positive check #2. """
        string = "123foo"
        state = core.State(string)
        parser = par.integer(True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 123)
        self.assertEqual(state_after.left, "foo")
        self.assertEqual(state_after.parsed, "123")

    #--------- various ---------#

    def test_everything(self):
        """ Test 'everything' parser generator. """
        string = "foobar"
        state = core.State(string)
        parser = par.everything()
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_literal_negative_1(self):
        """ Test 'literal' parser generator, negative check #1. """
        string = "foo"
        state = core.State(string)
        parser = par.literal("baz")
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_literal_positive_1(self):
        """ Test 'literal' parser generator, positive check #1. """
        string = "foo"
        state = core.State(string)
        parser = par.literal("fo")
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "o")
        self.assertEqual(state_after.parsed, "fo")

    def test_maybe_negative_1(self):
        """ Test 'maybe' parser generator, negative check #1. """
        string = "foo"
        state = core.State(string)
        parser = par.maybe(par.literal("baz"))
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, string)
        self.assertEqual(state_after.parsed, "")

    def test_maybe_positive_1(self):
        """ Test 'maybe' parser generator, positive check #1. """
        string = "foo"
        state = core.State(string)
        parser = par.maybe(par.literal("fo"))
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "fo")
        self.assertEqual(state_after.left, "o")

    def test_many_negative_1(self):
        """ Test 'many' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = par.many(par.literal("1"), 2, 1)

    def test_many_negative_2(self):
        """ Test 'many' parser generator, negative check #2. """
        string = "foofoo"
        state = core.State(string)
        parser = par.many(par.literal("foo"), 3, 3)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_many_positive_1(self):
        """ Test 'many' parser generator, positive check #1. """
        string = "foofoo"
        state = core.State(string)
        parser = par.many(par.literal("foo"))
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_many_positive_2(self):
        """ Test 'many' parser generator, positive check #2. """
        string = "foofoofoo"
        state = core.State(string)
        parser = par.many(par.literal("foo"), 1, 2)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "foofoo")
        self.assertEqual(state_after.left, "foo")

    def test_multi_negative_1(self):
        """ Test 'multi' parser generator, negative check #1. """
        string = "d"
        state = core.State(string)
        parser = par.multi(["a", "b"])
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_multi_positive_1(self):
        """ Test 'multi' parser generator, positive check #1. """
        string = "bd"
        state = core.State(string)
        parser = par.multi(["a", "b"])
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "d")
        self.assertEqual(state_after.parsed, "b")

    def test_repeat_while_negative_1(self):
        """ Test 'repeat_while' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = par.repeat_while(lambda state, window: True, -1)

    def test_repeat_while_negative_2(self):
        """ Test 'repeat_while' parser generator, negative check #2. """
        string = "aa"
        state = core.State(string)
        parser = par.repeat_while(lambda state, window: window == "a", 1, 3)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_repeat_while_negative_3(self):
        """ Test 'repeat_while' parser generator, negative check #3. """
        string = "aab"
        state = core.State(string)
        parser = par.repeat_while(lambda state, window: window == "a", 1, 3)
        state_after = core.parse(state, parser)
        self.assertIsNone(state_after)
        self.assertIsNone(state.value)
        self.assertEqual(state.left, string)
        self.assertEqual(state.parsed, "")

    def test_repeat_while_positive_1(self):
        """ Test 'repeat_while' parser generator, positive check #1. """
        string = "aa"
        state = core.State(string)
        parser = par.repeat_while(lambda state, window: window == "a")
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_repeat_while_positive_2(self):
        """ Test 'repeat_while' parser generator, positive check #2. """
        string = "aab"
        state = core.State(string)
        parser = par.repeat_while(lambda state, window: window == "a")
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, "aa")

    def test_repeat_while_positive_3(self):
        """ Test 'repeat_while' parser generator, positive check #3. """
        string = "bbb"
        state = core.State(string)
        parser = par.repeat_while(lambda state, window: window == "a")
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, string)
        self.assertEqual(state_after.parsed, "")


if __name__ == "__main__":
    unittest.main()
