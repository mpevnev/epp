#!/usr/bin/python

"""
Unit tests for epp library.
"""

import itertools as it
import unittest

import epp


class TestCore(unittest.TestCase):
    """ Test core parsers and functions. """

    def test_absorb(self):
        """ Test 'absorb' parser generator. """
        string = "12"
        state = epp.State(string, {})
        absorbee = epp.chain([
            epp.literal("12"),
            epp.modify(lambda state: state.set(value=int(state.parsed)))])
        def absorber(state, to_be_absorbed):
            """ A function which will absorb a parsed integer into main state. """
            state = state.deepcopy()
            state.value["key"] = to_be_absorbed.value
            return state
        parser = epp.absorb(absorber, absorbee)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, {"key": 12})
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, "")

    def test_branch_negative_1(self):
        """ Test 'branch' parser generator, negative check #1. """
        string = "4"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_branch_positive_1(self):
        """ Test 'branch' parser generator, positive check #1. """
        string = "21"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIs(state_after.value, None)
        self.assertEqual(state_after.parsed, "2")
        self.assertEqual(state_after.left, "1")

    def test_branch_positive_2(self):
        """ Test 'branch' parser generator, positive check #2. """
        # AKA 'order matters'.
        string = "ab3"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("ab"),
            epp.literal("a")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIs(state_after.value, None)
        self.assertEqual(state_after.parsed, "ab")
        self.assertEqual(state_after.left, "3")

    def test_catch_negative_1(self):
        """ Test 'catch' parser generator, negative check #1. """
        def inner_parser(state):
            """ A silly parser that only throws exceptions. """
            raise ValueError
        parser = epp.catch(inner_parser, [TypeError])
        string = "foobar"
        with self.assertRaises(ValueError):
            epp.parse(string, parser)

    def test_catch_positive_1(self):
        """ Test 'catch' parser generator, positive check #1. """
        def inner_parser(state):
            """ A silly parser that only thrown exceptions. """
            raise ValueError
        def on_thrown(state, exception):
            """ Exception handler. """
            return state.set(value=state.value + 10)
        string = "12"
        state = epp.State(string, value=0)
        parser = epp.catch(inner_parser, [ValueError], on_thrown, None)
        state_after = epp.parse(state, parser)
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
        state = epp.State(string, value=0)
        parser = epp.catch(epp.identity(), [Exception], None, on_not_thrown)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 10)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, string)

    def test_chain_negative_1(self):
        """ Test 'chain' parser generator, negative check #1. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("!"),
            epp.literal("2"),
            epp.literal("3")])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_chain_negative_2(self):
        """ Test 'chain' parser generator, negative check #2. """
        string = "1x3"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_chain_positive_1(self):
        """ Test 'chain' parser generator, positive check #1. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain(
            [
                epp.literal("1"),
                epp.literal("2"),
                epp.literal("3")
            ],
            combine=False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "3")
        self.assertEqual(state_after.left, "")

    def test_chain_positive_2(self):
        """ Test 'chain' parser generator, positive check #2. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain(
            [
                epp.literal("1"),
                epp.literal("2"),
                epp.literal("3")
            ],
            combine=True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_chain_positive_3(self):
        """ Test 'chain' parser generator, positive check #3. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain((epp.digit() for i in range(10)), stop_on_failure=True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_fail(self):
        """ Test 'fail' parser generator. """
        string = "irrelevant"
        state = epp.State(string)
        parser = epp.fail()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_identity(self):
        """ Test 'identity' parser generator. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.identity()
        state_after = epp.parse(state, parser)
        self.assertEqual(state_after, state)

    def test_lazy(self):
        """ Test 'lazy' parser generator. """
        def generator():
            """ Return a recursive parser. """
            maybe_end = epp.branch([epp.end_of_input(), epp.lazy(generator)])
            return epp.chain([epp.literal("1"), maybe_end])
        string = "111"
        state = epp.State(string)
        parser = generator()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_modify(self):
        """ Test 'modify' parser generator. """
        string = "doesn't change"
        state = epp.State(string, 0)
        parser = epp.modify(lambda state: state.set(value=state.value + 10))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 10)
        self.assertEqual(state_after.left, string)
        self.assertEqual(state_after.parsed, "")

    def test_noconsume(self):
        """ Test 'noconsume' parser generator. """
        string = "foo"
        state = epp.State(string)
        parser = epp.noconsume(epp.literal("foo"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, string)

    def test_stop(self):
        """ Test 'stop' parser generator. """
        string = "123"
        state = epp.State(string)
        chain = epp.chain(
            [
                epp.literal("1"),
                epp.literal("2"),
                epp.stop(),
                epp.literal("3")
            ],
            combine=True)
        state_after = epp.parse(state, chain)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "3")
        # note that 'combine' step of a chain is only performed if the chain
        # was not interrupted
        self.assertEqual(state_after.parsed, "2")

    def test_test_negative_1(self):
        """  Test 'test' parser generator, negative check #1. """
        test = lambda state: int(state.parsed) > 10
        string = "6"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("6"),
            epp.test(test)])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_test_positive_1(self):
        """ Test 'test' parser generator, positive check #1. """
        test = lambda state: int(state.parsed) > 10
        string = "12"
        state = epp.State(string)
        parser = epp.chain(
            [
                epp.literal("12"),
                epp.test(test)
            ],
            combine=True)
        state_after = epp.parse(state, parser)
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
        state = epp.State(string)
        parser = epp.alnum()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alnum_negative_2(self):
        """ Test 'alnum' parser generator, negative check #2. """
        string = '_'
        state = epp.State(string)
        parser = epp.alnum(False)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alnum_negative_3(self):
        """ Test 'alnum' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alnum(True)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alnum_positive_1(self):
        """ Test 'alnum' parser generator, positive check #1. """
        string = "1a"
        state = epp.State(string)
        parser = epp.chain([epp.alnum(), epp.alnum()], True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_alnum_positive_2(self):
        """ Test 'alnum' parser generator, positive check #2. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alnum(False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_alpha_negative_1(self):
        """ Test 'alpha' parser generator, negative check #1. """
        state = epp.State("")
        parser = epp.alpha()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alpha_negative_2(self):
        """ Test 'alpha' parser generator, negative check #2. """
        string = "1"
        state = epp.State(string)
        parser = epp.alpha()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alpha_negative_3(self):
        """ Test 'alpha' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alpha(True)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_alpha_positive_1(self):
        """ Test 'alpha' parser generator, positive check #1. """
        string = "ab"
        state = epp.State(string)
        parser = epp.alpha(True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "a")
        self.assertEqual(state_after.left, "b")

    def test_alpha_positive_2(self):
        """ Test 'alpha' parser generator, positive check #2. """
        string = "\U000000DFb"
        state = epp.State(string)
        parser = epp.alpha(False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "\U000000DF")
        self.assertEqual(state_after.left, "b")

    def test_any_char_negative_1(self):
        """ Test 'any_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.any_char()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_any_char_positive_1(self):
        """ Test 'any_char' parser generator, positive check #1. """
        string = "adsf"
        state = epp.State(string)
        parser = epp.any_char()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "dsf")
        self.assertEqual(state_after.parsed, "a")

    def test_cond_char_negative_1(self):
        """ Test 'cond_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.cond_char(lambda char: True)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_cond_char_negative_2(self):
        """ Test 'cond_char' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.cond_char(lambda char: char > "b")
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_cond_char_positive_1(self):
        """ Test 'cond_char' parser generator, positive check #1. """
        string = "ab"
        state = epp.State(string)
        parser = epp.cond_char(lambda char: char == "a")
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "a")
        self.assertEqual(state_after.left, "b")

    def test_digit_negative_1(self):
        """ Test 'digit' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.digit()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_digit_negative_2(self):
        """ Test 'digit' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.digit()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_digit_positive_1(self):
        """ Test 'digit' parser generator, positive check #1. """
        string = "1a"
        state = epp.State(string)
        parser = epp.digit()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "1")
        self.assertEqual(state_after.left, "a")

    def test_hex_digit_negative_1(self):
        """ Test 'hex_digit' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.hex_digit()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_hex_digit_negative_2(self):
        """ Test 'hex_digit' parser generator, negative check #2. """
        string = "z"
        state = epp.State(string)
        parser = epp.hex_digit()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_hex_digit_positive_1(self):
        """ Test 'hex_digit' parser generator, positive check #1. """
        string = "1aB"
        state = epp.State(string)
        parser = epp.many(epp.hex_digit())
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_newline_negative_1(self):
        """ Test 'newline' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.newline()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_newline_negative_2(self):
        """ Test 'newline' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.newline()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_newline_positive_1(self):
        """ Test 'newline' parser generator, positive check #1. """
        string = "\nb"
        state = epp.State(string)
        parser = epp.newline()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "\n")
        self.assertEqual(state_after.left, "b")

    def test_nonwhite_char_negative_1(self):
        """ Test 'nonwhite_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.nonwhite_char()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_nonwhite_char_negative_2(self):
        """ Test 'nonwhite_char' parser generator, negative check #2. """
        string = " "
        state = epp.State(string)
        parser = epp.nonwhite_char()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_nonwhite_char_positive_1(self):
        """ Test 'nonwhite_char' parser generator, positive check #1. """
        string = "b"
        state = epp.State(string)
        parser = epp.nonwhite_char()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_white_char_negative_1(self):
        """ Test 'white_char' parser generator, negative check #1. """
        string = "b"
        state = epp.State(string)
        parser = epp.white_char()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_white_char_negative_2(self):
        """ Test 'white_char' parser generator, negative check #2. """
        string = "\n"
        state = epp.State(string)
        parser = epp.white_char(False)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_white_char_negative_3(self):
        """ Test 'white_char' parser generator, negative check #3. """
        string = ""
        state = epp.State(string)
        parser = epp.white_char()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_white_char_positive_1(self):
        """ Test 'white_char' parser generator, positive check #1. """
        string = " b"
        state = epp.State(string)
        parser = epp.white_char()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, " ")

    def test_white_char_positive_2(self):
        """ Test 'white_char' parser generator, positive check #2. """
        string = "\nb"
        state = epp.State(string)
        parser = epp.white_char(True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, "\n")

    #--------- aggregates and variations of the above ---------#

    def test_hex_int_negative_1(self):
        """ Test 'hex_int' parser generator, negative check #1. """
        string = "ttt"
        state = epp.State(string)
        parser = epp.hex_int()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_hex_int_negative_2(self):
        """ Test 'hex_int' parser generator, negative check #2. """
        string = "00ab"
        state = epp.State(string)
        parser = epp.hex_int(must_have_prefix=True)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_hex_int_positive_1(self):
        """ Test 'hex_int' parser generator, positive check #1. """
        string = "0xA"
        state = epp.State(string)
        parser = epp.hex_int(must_have_prefix=True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_hex_int_positive_2(self):
        """ Test 'hex_int' parser generator, positive check #2. """
        string = "10"
        state = epp.State(string)
        parser = epp.hex_int(alter_state=True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 0x10)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_integer_negative_1(self):
        """ Test 'integer' parser generator, negative check #1. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.integer()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_integer_negative_2(self):
        """ Test 'integer' parser generator, negative check #2. """
        string = ""
        state = epp.State(string)
        parser = epp.integer()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_integer_positive_1(self):
        """ Test 'integer' parser generator, positive check #1. """
        string = "123foo"
        state = epp.State(string)
        parser = epp.integer(False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "foo")
        self.assertEqual(state_after.parsed, "123")

    def test_integer_positive_2(self):
        """ Test 'integer' parser generator, positive check #2. """
        string = "123foo"
        state = epp.State(string)
        parser = epp.integer(True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 123)
        self.assertEqual(state_after.left, "foo")
        self.assertEqual(state_after.parsed, "123")

    def test_line_negative_1(self):
        """ Test 'line' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.line()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_line_positive_1(self):
        """ Test 'line' parser generator, positive check #1. """
        string = "asdf\ndd"
        state = epp.State(string)
        parser = epp.line(False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.left, "dd")
        self.assertEqual(state_after.parsed, "asdf")
        self.assertIsNone(state_after.value)

    def test_line_positive_2(self):
        """ Test 'line' parser generator, positive check #2. """
        string = "asdf\ndd"
        state = epp.State(string)
        parser = epp.line(True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.left, "dd")
        self.assertEqual(state_after.parsed, "asdf\n")
        self.assertIsNone(state_after.value)

    def test_whitespace_negative_1(self):
        """ Test 'whitespace' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.whitespace()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_whitespace_negative_2(self):
        """ Test 'whitespace' parser generator, negative check #2. """
        string = "\n"
        state = epp.State(string)
        parser = epp.whitespace(1, False)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_whitespace_negative_3(self):
        """ Test 'whitespace' parser generator, negative check #3. """
        string = "b"
        state = epp.State(string)
        parser = epp.whitespace()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_whitespace_positive_1(self):
        """ Test 'whitespace' parser generator, positive check #1. """
        string = " \t b"
        state = epp.State(string)
        parser = epp.whitespace()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, " \t ")
        self.assertEqual(state_after.left, "b")

    def test_whitespace_positive_2(self):
        """ Test 'whitespace' parser generator, positive check #2. """
        string = " \n a"
        state = epp.State(string)
        parser = epp.whitespace(1, True)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, " \n ")
        self.assertEqual(state_after.left, "a")

    def test_whitespace_positive_3(self):
        """ Test 'whitespace' parser generator, positive check #3. """
        string = "b"
        state = epp.State(string)
        parser = epp.whitespace(0)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, string)

    #--------- various ---------#

    def test_end_of_input_negative_1(self):
        """ Test 'end_of_input' parser generator, negative check #1. """
        string = "a"
        state = epp.State(string)
        parser = epp.end_of_input()
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_end_of_input_positive_1(self):
        """ Test 'end_of_input' parser generator, positive check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.end_of_input()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, "")

    def test_everything(self):
        """ Test 'everything' parser generator. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.everything()
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_literal_negative_1(self):
        """ Test 'literal' parser generator, negative check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.literal("baz")
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_literal_positive_1(self):
        """ Test 'literal' parser generator, positive check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.literal("fo")
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "o")
        self.assertEqual(state_after.parsed, "fo")

    def test_maybe_negative_1(self):
        """ Test 'maybe' parser generator, negative check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.maybe(epp.literal("baz"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)

    def test_maybe_positive_1(self):
        """ Test 'maybe' parser generator, positive check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.maybe(epp.literal("fo"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "fo")
        self.assertEqual(state_after.left, "o")

    def test_many_negative_1(self):
        """ Test 'many' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.many(epp.literal("1"), 2, 1)

    def test_many_negative_2(self):
        """ Test 'many' parser generator, negative check #2. """
        string = "foofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"), 3, 3)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_many_positive_1(self):
        """ Test 'many' parser generator, positive check #1. """
        string = "foofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_many_positive_2(self):
        """ Test 'many' parser generator, positive check #2. """
        string = "foofoofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"), 1, 2)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "foofoo")
        self.assertEqual(state_after.left, "foo")

    def test_multi_negative_1(self):
        """ Test 'multi' parser generator, negative check #1. """
        string = "d"
        state = epp.State(string)
        parser = epp.multi(["a", "b"])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_multi_positive_1(self):
        """ Test 'multi' parser generator, positive check #1. """
        string = "bd"
        state = epp.State(string)
        parser = epp.multi(["a", "b"])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "d")
        self.assertEqual(state_after.parsed, "b")

    def test_repeat_while_negative_1(self):
        """ Test 'repeat_while' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.repeat_while(lambda state, window: True, -1)

    def test_repeat_while_negative_2(self):
        """ Test 'repeat_while' parser generator, negative check #2. """
        string = "aa"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a", 1, 3)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_repeat_while_negative_3(self):
        """ Test 'repeat_while' parser generator, negative check #3. """
        string = "aab"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a", 1, 3)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_repeat_while_positive_1(self):
        """ Test 'repeat_while' parser generator, positive check #1. """
        string = "aa"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "")
        self.assertEqual(state_after.parsed, string)

    def test_repeat_while_positive_2(self):
        """ Test 'repeat_while' parser generator, positive check #2. """
        string = "aab"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, "b")
        self.assertEqual(state_after.parsed, "aa")

    def test_repeat_while_positive_3(self):
        """ Test 'repeat_while' parser generator, positive check #3. """
        string = "bbb"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.left, string)
        self.assertEqual(state_after.parsed, "")

    def test_take_negative_1(self):
        """ Test 'take' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.take(-1)

    def test_take_negative_2(self):
        """ Test 'take' parser generator, negative check #2. """
        string = "123"
        state = epp.State(string)
        parser = epp.take(5, True)
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_take_positive_1(self):
        """ Test 'take' parser generator, positive check #1. """
        string = "12345"
        state = epp.State(string)
        parser = epp.take(3)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "123")
        self.assertEqual(state_after.left, "45")

    def test_take_positive_2(self):
        """ Test 'take' parser generator, positive check #2. """
        string = "123"
        state = epp.State(string)
        parser = epp.take(5, False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_weave_negative_1(self):
        """ Test 'weave' parser generator, negative check #1. """
        string = "12131"
        state = epp.State(string)
        parser = epp.weave(epp.reuse_iter(it.repeat, epp.literal("1"), 3),
                           epp.literal("2"))
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_weave_negative_2(self):
        """ Test 'weave' parser generator, negative check #2. """
        string = "22121"
        state = epp.State(string)
        parser = epp.weave(epp.reuse_iter(it.repeat, epp.literal("1"), 3),
                           epp.literal("2"))
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_weave_negative_3(self):
        """ Test 'weave' parser generator, negative check #3. """
        string = "121215"
        state = epp.State(string)
        parser = epp.weave(epp.reuse_iter(it.repeat, epp.literal("1"), 3),
                           epp.literal("2"),
                           trailing=epp.literal("3"))
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_weave_positive_1(self):
        """ Test 'weave' parser generator, positive check #1. """
        string = "12121"
        state = epp.State(string)
        parser = epp.weave(epp.reuse_iter(it.repeat, epp.literal("1"), 3),
                epp.literal("2"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_weave_positive_2(self):
        """ Test 'weave' parser generator, positive check #2. """
        string = "121213"
        state = epp.State(string)
        parser = epp.weave(epp.reuse_iter(it.repeat, epp.literal("1"), 3),
                epp.literal("2"),
                trailing=epp.literal("3"))
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")


class TestLookahead(unittest.TestCase):
    """ Test lookahead mechanism. """

    def test_greedy_negative_1(self):
        """ Test 'greedy' lookahead mode, negative check #1. """
        string = "2"
        state = epp.State(string)
        parser = epp.chain([epp.greedy(epp.literal("1"))])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_greedy_positive_1(self):
        """ Test 'greedy' lookahead mode, positive check #1. """
        string = "foo!"
        state = epp.State(string)
        parser = epp.chain([epp.greedy(epp.everything()), epp.literal("!")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_greedy_positive_2(self):
        """ Test 'greedy' lookahead mode, positive check #2. """
        string = "fofofo"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("fo"))),
             epp.literal("fo")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, string)
        self.assertEqual(state_after.left, "")

    def test_interplay_negative_1(self):
        """ Test 'greedy' and 'reluctant' interplay, negative check 1. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("a"))),
             epp.reluctant(epp.many(epp.literal("b"))),
             epp.literal("c")])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_interplay_positive_1(self):
        """ Test 'greedy' and 'reluctant' interplay, positive check #1. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("a"))),
             epp.reluctant(epp.many(epp.literal("b"), min_hits=1)),
             epp.everything()], False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "bd")
        self.assertEqual(state_after.left, "")

    def test_interplay_positive_2(self):
        """ Test 'greedy' and 'reluctant' interplay, positive check #2. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.reluctant(epp.many(epp.literal("a"))),
             epp.greedy(epp.many(epp.literal("b"), min_hits=1)),
             epp.everything()], False)
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "d")
        self.assertEqual(state_after.left, "")

    def test_reluctant_negative_1(self):
        """ Test 'reluctant' lookahead mode, negative check #1. """
        string = "2"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.literal("1"))])
        state_after = epp.parse(state, parser)
        self.assertIsNone(state_after)

    def test_reluctant_positive_1(self):
        """ Test 'reluctant' lookahead mode, positive check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.everything())])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "")
        self.assertEqual(state_after.left, string)

    def test_reluctant_positive_2(self):
        """ Test 'reluctant' lookahead mode, positive check #2. """
        string = "foo!bar"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.everything()), epp.literal("!")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "foo!")
        self.assertEqual(state_after.left, "bar")

    def test_reluctant_positive_3(self):
        """ Test 'reluctant' lookahead mode, positive check #3. """
        string = "fofofo"
        state = epp.State(string)
        parser = epp.chain(
            [epp.reluctant(epp.many(epp.literal("fo"), min_hits=1)),
             epp.literal("fo")])
        state_after = epp.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state_after.parsed, "fofo")
        self.assertEqual(state_after.left, "fo")


if __name__ == "__main__":
    unittest.main()
