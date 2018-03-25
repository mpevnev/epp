#!/usr/bin/python

"""
Unit tests for epp library.
"""

import collections as coll
import itertools as it
import unittest

import epp


class TestState(unittest.TestCase):
    """ Test State class. """

    def test_consume_negative_1(self):
        """ Test 'consume' method, negative check #1. """
        string = "foobar"
        state = epp.State(string)
        with self.assertRaises(ValueError):
            _ = state.consume(-1)

    def test_consume_negative_2(self):
        """ Test 'consume' method, negative check #2. """
        string = "a"
        state = epp.State(string)
        with self.assertRaises(ValueError):
            _ = state.consume(10)

    def test_consume_positive_1(self):
        """ Test 'consume' method, positive check #1. """
        string = "foobar"
        state = epp.State(string)
        after = state.consume(3)
        self.assertIsNotNone(after)
        self.assertEqual(after.left, "bar")
        self.assertEqual(after.parsed, "foo")

    def test_replace_positive_1(self):
        """ Test '_replace' method, positive check #1. """
        state = epp.State("foobar", effect=lambda val, st: val)
        after = state._replace(left_start=2)
        self.assertIsNotNone(after)
        self.assertEqual(after.left, "obar")
        self.assertEqual(after.parsed, "")
        self.assertIsNone(after.effect)

    def test_replace_positive_2(self):
        """ Test '_replace' method, positive check #2. """
        effect_1 = lambda val, st: val
        effect_2 = lambda val, st: val + 2
        state = epp.State("foobar", effect_1)
        after = state._replace(effect=effect_2)
        self.assertIsNotNone(after)
        self.assertEqual(after.left, "foobar")
        self.assertEqual(after.parsed, "")
        self.assertIs(after.effect, effect_2)

    def test_split_positive_1(self):
        """ Test 'split' method, positive check #1. """
        string = "foobar"
        original = epp.State(string, effect=lambda val, st: val)
        a, b = original.split(3)
        self.assertIsNotNone(a)
        self.assertEqual(a.left, "foo")
        self.assertIsNotNone(a.effect)
        self.assertIsNotNone(b)
        self.assertEqual(b.left, "bar")
        self.assertIsNone(b.effect)


class TestCore(unittest.TestCase):
    """ Test core parsers and functions. """

    def test_branch_negative_1(self):
        """ Test 'branch' parser generator, negative check #1. """
        string = "4"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_branch_negative_2(self):
        """ Test 'branch' parser generator, negative check #2. """
        string = "4"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")], save_iterator=False)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_branch_negative_3(self):
        """
        Test 'branch' parser generator, negative check #3.

        Test that 'branch' fails if the supplied iterable is empty.
        """
        parser = epp.branch([])
        output = epp.parse(None, "", parser, verbose=True)
        self.assertIsNotNone(output)
        self.assertTrue(isinstance(output, epp.ParsingFailure))
        self.assertEqual(output.code, epp.BranchError.EMPTY)

    def test_branch_negative_4(self):
        """
        Test 'branch' parser generator, negative check #4.

        Test that 'branch fails if several parsers from the supplied iterable
        succeed and the 'strictly_one' flag is set.
        """
        parser = epp.branch(
            [epp.literal("a"),
             epp.everything()],
            strictly_one=True)
        output = epp.parse(None, "a", parser, verbose=True)
        self.assertIsNotNone(output)
        self.assertTrue(isinstance(output, epp.ParsingFailure))
        self.assertEqual(output.code, epp.BranchError.MORE_THAN_ONE_SUCCEEDED)

    def test_branch_positive_1(self):
        """ Test 'branch' parser generator, positive check #1. """
        seed = 12
        string = "21"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        output = epp.parse(seed, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertEqual(value, seed)
        self.assertEqual(after.parsed, "2")
        self.assertEqual(after.left, "1")

    def test_branch_positive_2(self):
        """ Test 'branch' parser generator, positive check #2. """
        # AKA 'order matters'.
        seed = 12
        string = "ab3"
        state = epp.State(string)
        parser = epp.branch([
            epp.literal("ab"),
            epp.literal("a")])
        output = epp.parse(seed, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertEqual(value, seed)
        self.assertEqual(after.parsed, "ab")
        self.assertEqual(after.left, "3")

    def test_branch_positive_3(self):
        """
        Test 'branch' parser generator, positive check #3.

        Test behaviour of a saving branch on multiple uses.
        """
        string = "b"
        state = epp.State(string)
        parser = epp.branch(
            [epp.literal("a"),
             epp.literal("b")])
        output1 = epp.parse(None, state, parser)
        self.assertIsNotNone(output1)
        output2 = epp.parse(None, state, parser)
        self.assertIsNotNone(output2)
        self.assertEqual(output1, output2)

    def test_catch_negative_1(self):
        """ Test 'catch' parser generator, negative check #1. """
        def inner_parser(state):
            """ A silly parser that only throws exceptions. """
            raise ValueError
        parser = epp.catch(inner_parser, [TypeError])
        string = "foobar"
        with self.assertRaises(ValueError):
            epp.parse(None, string, parser)

    def test_catch_positive_1(self):
        """ Test 'catch' parser generator, positive check #1. """
        def inner_parser(state):
            """ A silly parser that only thrown exceptions. """
            raise ValueError
        def on_thrown(state, exception):
            """ Exception handler. """
            return state._replace(effect=lambda val, st: val + 10)
        string = "12"
        state = epp.State(string)
        parser = epp.catch(inner_parser, [ValueError], on_thrown, None)
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertEqual(value, 10)
        self.assertEqual(after.left, string)
        self.assertEqual(after.parsed, "")

    def test_catch_positive_2(self):
        """ Test 'catch' parser generator, positive check #2. """
        def on_not_thrown(state):
            """ Unexception handler. """
            return state._replace(effect=lambda val, st: val + 10)
        string = "12"
        state = epp.State(string)
        parser = epp.catch(epp.identity(), [Exception], None, on_not_thrown)
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertEqual(value, 10)
        self.assertEqual(after.parsed, "")
        self.assertEqual(after.left, string)

    def test_chain_negative_1(self):
        """ Test 'chain' parser generator, negative check #1. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("!"),
            epp.literal("2"),
            epp.literal("3")])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_chain_negative_2(self):
        """ Test 'chain' parser generator, negative check #2. """
        string = "1x3"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("1"),
            epp.literal("2"),
            epp.literal("3")])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

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
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "3")
        self.assertEqual(after.left, "")

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
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_chain_positive_3(self):
        """ Test 'chain' parser generator, positive check #3. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain((epp.digit() for i in range(10)), stop_on_failure=True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_chain_positive_4(self):
        """ Test 'chain' parser generator, positive check #4. """
        string = "123"
        state = epp.State(string)
        parser = epp.chain(
            [
                epp.literal("1"),
                epp.literal("2"),
                epp.stop(),
                epp.literal("3")
            ],
            all_or_nothing=False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "3")
        self.assertEqual(after.parsed, "12")

    def test_fail(self):
        """ Test 'fail' parser generator. """
        string = "irrelevant"
        state = epp.State(string)
        parser = epp.fail()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_identity(self):
        """ Test 'identity' parser generator. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.identity()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after, state)

    def test_lazy(self):
        """ Test 'lazy' parser generator. """
        def generator():
            """ Return a recursive parser. """
            maybe_end = epp.branch([epp.end_of_input(), epp.lazy(generator)])
            return epp.chain([epp.literal("1"), maybe_end])
        string = "111"
        state = epp.State(string)
        parser = generator()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_modify_error(self):
        """ Test 'modify_error' parser generator. """
        string = "irrelevant"
        state = epp.State(string)
        parser = epp.modify_error(epp.fail(), lambda err: epp.ParsingFailure(err.state, "!"))
        output = epp.parse(None, state, parser, verbose=True)
        self.assertEqual(output.args, ("!",))

    def test_noconsume(self):
        """ Test 'noconsume' parser generator. """
        string = "foo"
        state = epp.State(string)
        parser = epp.noconsume(epp.literal("foo"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, string)

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
            combine=True, all_or_nothing=False)
        output = epp.parse(None, state, chain)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "3")
        self.assertEqual(after.parsed, "12")

    def test_subparse_negative_1(self):
        """ Test 'subparse' parser generator, negative check #1. """
        string = "foobar"
        state = epp.State(string)
        subparser = epp.literal("baz")
        def absorber(main_val, main_st, val, st):
            """ Absorber. """
            return main_val + 10
        parser = epp.chain(
            [
                epp.literal("foo"),
                epp.subparse(0, subparser, absorber)
            ])
        output = epp.parse(0, state, parser)
        self.assertIsNone(output)

    def test_subparse_positive_1(self):
        """ Test 'subparse' parser generator, positive check #1. """
        string = "a111"
        state = epp.State(string)
        subparser = epp.chain(
            [
                epp.integer(),
                epp.effect(lambda val, st: int(st.parsed))
            ])
        def absorber(main_val, main_st, val, st):
            """ Absorber. """
            main_val[main_st.parsed] = val
            return main_val
        parser = epp.chain(
            [
                epp.literal("a"),
                epp.subparse(0, subparser, absorber)
            ])
        output = epp.parse({}, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, {"a": 111})


    def test_test_negative_1(self):
        """  Test 'test' parser generator, negative check #1. """
        test = lambda state: int(state.parsed) > 10
        string = "6"
        state = epp.State(string)
        parser = epp.chain([
            epp.literal("6"),
            epp.test(test)])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

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
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "12")
        self.assertEqual(after.left, "")


class TestParsers(unittest.TestCase):
    """ Test concrete parsers. """

    #--------- single-character parsers ---------#

    def test_alnum_negative_1(self):
        """ Test 'alnum' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.alnum()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alnum_negative_2(self):
        """ Test 'alnum' parser generator, negative check #2. """
        string = '_'
        state = epp.State(string)
        parser = epp.alnum(False)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alnum_negative_3(self):
        """ Test 'alnum' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alnum(True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alnum_positive_1(self):
        """ Test 'alnum' parser generator, positive check #1. """
        string = "1a"
        state = epp.State(string)
        parser = epp.chain([epp.alnum(), epp.alnum()], True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_alnum_positive_2(self):
        """ Test 'alnum' parser generator, positive check #2. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alnum(False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_alpha_negative_1(self):
        """ Test 'alpha' parser generator, negative check #1. """
        state = epp.State("")
        parser = epp.alpha()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alpha_negative_2(self):
        """ Test 'alpha' parser generator, negative check #2. """
        string = "1"
        state = epp.State(string)
        parser = epp.alpha()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alpha_negative_3(self):
        """ Test 'alpha' parser generator, negative check #3. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alpha(True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alpha_positive_1(self):
        """ Test 'alpha' parser generator, positive check #1. """
        string = "ab"
        state = epp.State(string)
        parser = epp.alpha(True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "a")
        self.assertEqual(after.left, "b")

    def test_alpha_positive_2(self):
        """ Test 'alpha' parser generator, positive check #2. """
        string = "\U000000DFb"
        state = epp.State(string)
        parser = epp.alpha(False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "\U000000DF")
        self.assertEqual(after.left, "b")

    def test_any_char_negative_1(self):
        """ Test 'any_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.any_char()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_any_char_positive_1(self):
        """ Test 'any_char' parser generator, positive check #1. """
        string = "adsf"
        state = epp.State(string)
        parser = epp.any_char()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "dsf")
        self.assertEqual(after.parsed, "a")

    def test_cond_char_negative_1(self):
        """ Test 'cond_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.cond_char(lambda char: True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_cond_char_negative_2(self):
        """ Test 'cond_char' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.cond_char(lambda char: char > "b")
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_cond_char_positive_1(self):
        """ Test 'cond_char' parser generator, positive check #1. """
        string = "ab"
        state = epp.State(string)
        parser = epp.cond_char(lambda char: char == "a")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "a")
        self.assertEqual(after.left, "b")

    def test_digit_negative_1(self):
        """ Test 'digit' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.digit()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_digit_negative_2(self):
        """ Test 'digit' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.digit()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_digit_positive_1(self):
        """ Test 'digit' parser generator, positive check #1. """
        string = "1a"
        state = epp.State(string)
        parser = epp.digit()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "1")
        self.assertEqual(after.left, "a")

    def test_hex_digit_negative_1(self):
        """ Test 'hex_digit' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.hex_digit()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_hex_digit_negative_2(self):
        """ Test 'hex_digit' parser generator, negative check #2. """
        string = "z"
        state = epp.State(string)
        parser = epp.hex_digit()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_hex_digit_positive_1(self):
        """ Test 'hex_digit' parser generator, positive check #1. """
        string = "1aB"
        state = epp.State(string)
        parser = epp.many(epp.hex_digit())
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_newline_negative_1(self):
        """ Test 'newline' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.newline()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_newline_negative_2(self):
        """ Test 'newline' parser generator, negative check #2. """
        string = "a"
        state = epp.State(string)
        parser = epp.newline()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_newline_positive_1(self):
        """ Test 'newline' parser generator, positive check #1. """
        string = "\nb"
        state = epp.State(string)
        parser = epp.newline()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "\n")
        self.assertEqual(after.left, "b")

    def test_nonwhite_char_negative_1(self):
        """ Test 'nonwhite_char' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.nonwhite_char()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_nonwhite_char_negative_2(self):
        """ Test 'nonwhite_char' parser generator, negative check #2. """
        string = " "
        state = epp.State(string)
        parser = epp.nonwhite_char()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_nonwhite_char_positive_1(self):
        """ Test 'nonwhite_char' parser generator, positive check #1. """
        string = "b"
        state = epp.State(string)
        parser = epp.nonwhite_char()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_white_char_negative_1(self):
        """ Test 'white_char' parser generator, negative check #1. """
        string = "b"
        state = epp.State(string)
        parser = epp.white_char()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_white_char_negative_2(self):
        """ Test 'white_char' parser generator, negative check #2. """
        string = "\n"
        state = epp.State(string)
        parser = epp.white_char(False)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_white_char_negative_3(self):
        """ Test 'white_char' parser generator, negative check #3. """
        string = ""
        state = epp.State(string)
        parser = epp.white_char()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_white_char_positive_1(self):
        """ Test 'white_char' parser generator, positive check #1. """
        string = " b"
        state = epp.State(string)
        parser = epp.white_char()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "b")
        self.assertEqual(after.parsed, " ")

    def test_white_char_positive_2(self):
        """ Test 'white_char' parser generator, positive check #2. """
        string = "\nb"
        state = epp.State(string)
        parser = epp.white_char(True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "b")
        self.assertEqual(after.parsed, "\n")

    #--------- aggregates and variations of the above ---------#


    def test_alnum_word_negative_1(self):
        """ Test 'alnum_word' parser generator, negative check #1. """
        string = "!"
        state = epp.State(string)
        parser = epp.alnum_word()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alnum_word_negative_2(self):
        """ Test 'alnum_word' parser generator, negative check #2. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alnum_word(True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alnum_word_positive_1(self):
        """ Test 'alnum_word' parser generator, positive check #1. """
        string = "1a!"
        state = epp.State(string)
        parser = epp.alnum_word()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.parsed, "1a")
        self.assertEqual(after.left, "!")

    def test_alpha_word_negative_1(self):
        """ Test 'alpha_word' parser generator, negative check #1. """
        string = "!"
        state = epp.State(string)
        parser = epp.alpha_word()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alpha_word_negative_2(self):
        """ Test 'alpha_word' parser generator, negative check #2. """
        string = "\U000000DF" # Eszet
        state = epp.State(string)
        parser = epp.alpha_word(True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_alpha_word_positive_1(self):
        """ Test 'alpha_word' parser generator, positive check #1. """
        string = "a1"
        state = epp.State(string)
        parser = epp.alpha_word()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "1")
        self.assertEqual(after.parsed, "a")

    def test_any_word_negative_1(self):
        """ Test 'any_word' parser generator, negative check #1. """
        string = " 2"
        state = epp.State(string)
        parser = epp.any_word()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_any_word_positive_1(self):
        """ Test 'any_word' parser generator, positive check #1. """
        string = "a1, !"
        state = epp.State(string)
        parser = epp.any_word()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, " !")
        self.assertEqual(after.parsed, "a1,")

    def test_hex_int_negative_1(self):
        """ Test 'hex_int' parser generator, negative check #1. """
        string = "ttt"
        state = epp.State(string)
        parser = epp.hex_int()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_hex_int_negative_2(self):
        """ Test 'hex_int' parser generator, negative check #2. """
        string = "00ab"
        state = epp.State(string)
        parser = epp.hex_int(must_have_prefix=True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_hex_int_positive_1(self):
        """ Test 'hex_int' parser generator, positive check #1. """
        string = "0xA"
        state = epp.State(string)
        parser = epp.hex_int(must_have_prefix=True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_integer_negative_1(self):
        """ Test 'integer' parser generator, negative check #1. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.integer()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_integer_negative_2(self):
        """ Test 'integer' parser generator, negative check #2. """
        string = ""
        state = epp.State(string)
        parser = epp.integer()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_integer_positive_1(self):
        """ Test 'integer' parser generator, positive check #1. """
        string = "123foo"
        state = epp.State(string)
        parser = epp.integer()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "foo")
        self.assertEqual(after.parsed, "123")

    def test_line_negative_1(self):
        """ Test 'line' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.line()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_line_positive_1(self):
        """ Test 'line' parser generator, positive check #1. """
        string = "asdf\ndd"
        state = epp.State(string)
        parser = epp.line(False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "dd")
        self.assertEqual(after.parsed, "asdf")

    def test_line_positive_2(self):
        """ Test 'line' parser generator, positive check #2. """
        string = "asdf\ndd"
        state = epp.State(string)
        parser = epp.line(True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "dd")
        self.assertEqual(after.parsed, "asdf\n")

    def test_whitespace_negative_1(self):
        """ Test 'whitespace' parser generator, negative check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.whitespace()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_whitespace_negative_2(self):
        """ Test 'whitespace' parser generator, negative check #2. """
        string = "\n"
        state = epp.State(string)
        parser = epp.whitespace(1, False)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_whitespace_negative_3(self):
        """ Test 'whitespace' parser generator, negative check #3. """
        string = "b"
        state = epp.State(string)
        parser = epp.whitespace()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_whitespace_positive_1(self):
        """ Test 'whitespace' parser generator, positive check #1. """
        string = " \t b"
        state = epp.State(string)
        parser = epp.whitespace()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, " \t ")
        self.assertEqual(after.left, "b")

    def test_whitespace_positive_2(self):
        """ Test 'whitespace' parser generator, positive check #2. """
        string = " \n a"
        state = epp.State(string)
        parser = epp.whitespace(1, True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, " \n ")
        self.assertEqual(after.left, "a")

    def test_whitespace_positive_3(self):
        """ Test 'whitespace' parser generator, positive check #3. """
        string = "b"
        state = epp.State(string)
        parser = epp.whitespace(0)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "")
        self.assertEqual(after.left, string)

    #--------- various ---------#


    def test_balanced_negative_1(self):
        """ Test 'balanced' parser generator, negative check #1. """
        string = "b"
        state = epp.State(string)
        parser = epp.balanced("(", ")")
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_balanced_negative_2(self):
        """ Test 'balanced' parser generator, negative check #2. """
        string = "(()"
        state = epp.State(string)
        parser = epp.balanced("(", ")")
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_balanced_positive_1(self):
        """ Test 'balanced' parser generator, positive check #1. """
        string = "(1()22)3"
        state = epp.State(string)
        parser = epp.balanced("(", ")")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "3")
        self.assertEqual(after.parsed, "1()22")

    def test_balanced_positive_2(self):
        """ Test 'balanced' parser generator, positive check #2. """
        string = "(1()22)3"
        state = epp.State(string)
        parser = epp.balanced("(", ")", True)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "3")
        self.assertEqual(after.parsed, "(1()22)")

    def test_balanced_positive_3(self):
        """ Test 'balanced' parser generator, positive check #3. """
        string = "()"
        state = epp.State(string)
        parser = epp.balanced("(", ")")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, "")

    def test_end_of_input_negative_1(self):
        """ Test 'end_of_input' parser generator, negative check #1. """
        string = "a"
        state = epp.State(string)
        parser = epp.end_of_input()
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_end_of_input_positive_1(self):
        """ Test 'end_of_input' parser generator, positive check #1. """
        string = ""
        state = epp.State(string)
        parser = epp.end_of_input()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "")
        self.assertEqual(after.left, "")

    def test_everything(self):
        """ Test 'everything' parser generator. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.everything()
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_literal_negative_1(self):
        """ Test 'literal' parser generator, negative check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.literal("baz")
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_literal_positive_1(self):
        """ Test 'literal' parser generator, positive check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.literal("fo")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "o")
        self.assertEqual(after.parsed, "fo")

    def test_maybe_positive_1(self):
        """ Test 'maybe' parser generator, negative check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.maybe(epp.literal("baz"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, string)
        self.assertEqual(after.parsed, "")

    def test_maybe_positive_2(self):
        """ Test 'maybe' parser generator, positive check #2. """
        string = "foo"
        state = epp.State(string)
        parser = epp.maybe(epp.literal("fo"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "fo")
        self.assertEqual(after.left, "o")

    def test_many_negative_1(self):
        """ Test 'many' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.many(epp.literal("1"), 2, 1)

    def test_many_negative_2(self):
        """ Test 'many' parser generator, negative check #2. """
        string = "foofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"), 3, 3)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_many_positive_1(self):
        """ Test 'many' parser generator, positive check #1. """
        string = "foofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_many_positive_2(self):
        """ Test 'many' parser generator, positive check #2. """
        string = "foofoofoo"
        state = epp.State(string)
        parser = epp.many(epp.literal("foo"), 1, 2)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "foofoo")
        self.assertEqual(after.left, "foo")

    def test_multi_negative_1(self):
        """ Test 'multi' parser generator, negative check #1. """
        string = "d"
        state = epp.State(string)
        parser = epp.multi(["a", "b"])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_multi_positive_1(self):
        """ Test 'multi' parser generator, positive check #1. """
        string = "bd"
        state = epp.State(string)
        parser = epp.multi(["a", "b"])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "d")
        self.assertEqual(after.parsed, "b")

    def test_repeat_while_negative_1(self):
        """ Test 'repeat_while' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.repeat_while(lambda state, window: True, -1)

    def test_repeat_while_negative_2(self):
        """ Test 'repeat_while' parser generator, negative check #2. """
        string = "aa"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a", 1, 3)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_repeat_while_negative_3(self):
        """ Test 'repeat_while' parser generator, negative check #3. """
        string = "aab"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a", 1, 3)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_repeat_while_positive_1(self):
        """ Test 'repeat_while' parser generator, positive check #1. """
        string = "aa"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_repeat_while_positive_2(self):
        """ Test 'repeat_while' parser generator, positive check #2. """
        string = "aab"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, "b")
        self.assertEqual(after.parsed, "aa")

    def test_repeat_while_positive_3(self):
        """ Test 'repeat_while' parser generator, positive check #3. """
        string = "bbb"
        state = epp.State(string)
        parser = epp.repeat_while(lambda state, window: window == "a")
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.left, string)
        self.assertEqual(after.parsed, "")

    def test_take_negative_1(self):
        """ Test 'take' parser generator, negative check #1. """
        with self.assertRaises(ValueError):
            _ = epp.take(-1)

    def test_take_negative_2(self):
        """ Test 'take' parser generator, negative check #2. """
        string = "123"
        state = epp.State(string)
        parser = epp.take(5, True)
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_take_positive_1(self):
        """ Test 'take' parser generator, positive check #1. """
        string = "12345"
        state = epp.State(string)
        parser = epp.take(3)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "123")
        self.assertEqual(after.left, "45")

    def test_take_positive_2(self):
        """ Test 'take' parser generator, positive check #2. """
        string = "123"
        state = epp.State(string)
        parser = epp.take(5, False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_weave_negative_1(self):
        """ Test 'weave' parser generator, negative check #1. """
        string = "12131"
        state = epp.State(string)
        parser = epp.weave(it.repeat(epp.literal("1"), 3),
                           epp.literal("2"))
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_weave_negative_2(self):
        """ Test 'weave' parser generator, negative check #2. """
        string = "22121"
        state = epp.State(string)
        parser = epp.weave(it.repeat(epp.literal("1"), 3),
                           epp.literal("2"))
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_weave_negative_3(self):
        """ Test 'weave' parser generator, negative check #3. """
        string = "121215"
        state = epp.State(string)
        parser = epp.weave(it.repeat(epp.literal("1"), 3),
                           epp.literal("2"),
                           trailing=epp.literal("3"))
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_weave_positive_1(self):
        """ Test 'weave' parser generator, positive check #1. """
        string = "12121"
        state = epp.State(string)
        parser = epp.weave(it.repeat(epp.literal("1"), 3),
                epp.literal("2"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_weave_positive_2(self):
        """ Test 'weave' parser generator, positive check #2. """
        string = "121213"
        state = epp.State(string)
        parser = epp.weave(it.repeat(epp.literal("1"), 3),
                epp.literal("2"),
                trailing=epp.literal("3"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_weave_positive_3(self):
        """ Test 'weave' parser generator, positive check #3. """
        string = "1"
        state = epp.State(string)
        parser = epp.weave([epp.literal("1")], epp.literal("irrelevant"))
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")


class TestLookahead(unittest.TestCase):
    """ Test lookahead mechanism. """

    def test_branch_positive_1(self):
        """ Test lookahead in branches. """
        string = "2b"
        state = epp.State(string)
        parser = epp.branch(
            [epp.literal("1"),
             epp.chain([epp.greedy(epp.everything()), epp.literal("b")]),
             epp.literal("3")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_greediness_in_the_middle(self):
        """ Test what happens if a greedy parser is bracketed. """
        string = "foo bar baz"
        white = epp.whitespace(min_num=1)
        parser = epp.chain(
            [epp.literal("foo"),
             white,
             epp.chain([epp.greedy(epp.everything()), 
                        epp.effect(lambda val, st: st.parsed)]),
             white,
             epp.literal("baz")])
        output = epp.parse(None, string, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, "bar")

    def test_greedy_negative_1(self):
        """ Test 'greedy' lookahead mode, negative check #1. """
        string = "2"
        state = epp.State(string)
        parser = epp.chain([epp.greedy(epp.literal("1"))])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_greedy_positive_1(self):
        """ Test 'greedy' lookahead mode, positive check #1. """
        string = "foo!"
        state = epp.State(string)
        parser = epp.chain([epp.greedy(epp.everything()), epp.literal("!")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_greedy_positive_2(self):
        """ Test 'greedy' lookahead mode, positive check #2. """
        string = "fofofo"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("fo"))),
             epp.literal("fo")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, string)
        self.assertEqual(after.left, "")

    def test_interplay_negative_1(self):
        """ Test 'greedy' and 'reluctant' interplay, negative check 1. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("a"))),
             epp.reluctant(epp.many(epp.literal("b"))),
             epp.literal("c")])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_interplay_positive_1(self):
        """ Test 'greedy' and 'reluctant' interplay, positive check #1. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.greedy(epp.many(epp.literal("a"))),
             epp.reluctant(epp.many(epp.literal("b"), min_hits=1)),
             epp.everything()], False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "bd")
        self.assertEqual(after.left, "")

    def test_interplay_positive_2(self):
        """ Test 'greedy' and 'reluctant' interplay, positive check #2. """
        string = "aabbd"
        state = epp.State(string)
        parser = epp.chain(
            [epp.reluctant(epp.many(epp.literal("a"))),
             epp.greedy(epp.many(epp.literal("b"), min_hits=1)),
             epp.everything()], 
            combine=False)
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "d")
        self.assertEqual(after.left, "")

    def test_lazy_with_lookahead_inside(self):
        """ Test lookahead interaction with lazyness. """
        deque = coll.deque([1, 2, 3])
        def specific_parser(i):
            """ A parser for a specific element of the deque. """
            return epp.chain(
                [epp.literal(str(i)),
                 epp.effect(lambda val, st: i)],
                save_iterator=False)
        def generator():
            """ A parser generator. """
            variants = map(specific_parser, deque)
            catchall = epp.chain(
                [epp.greedy(epp.everything()),
                 epp.effect(lambda val, st: -1)],
                save_iterator=False)
            return epp.branch(it.chain(variants, [catchall]))
        parser = epp.lazy(generator)
        string = "5a"
        output = epp.parse(None, string, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertEqual(value, -1)

    def test_nested_positive_1(self):
        """ Test lookahead in nested chains, positive check #1. """
        string = "ab"
        state = epp.State(string)
        parser = epp.chain(
            [epp.chain([epp.greedy(epp.everything())]),
             epp.literal("b")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        _, after = output
        self.assertEqual(after.left, "")
        self.assertEqual(after.parsed, string)

    def test_reluctant_negative_1(self):
        """ Test 'reluctant' lookahead mode, negative check #1. """
        string = "2"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.literal("1"))])
        output = epp.parse(None, state, parser)
        self.assertIsNone(output)

    def test_reluctant_positive_1(self):
        """ Test 'reluctant' lookahead mode, positive check #1. """
        string = "foo"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.everything())])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "")
        self.assertEqual(after.left, string)

    def test_reluctant_positive_2(self):
        """ Test 'reluctant' lookahead mode, positive check #2. """
        string = "foo!bar"
        state = epp.State(string)
        parser = epp.chain([epp.reluctant(epp.everything()), epp.literal("!")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "foo!")
        self.assertEqual(after.left, "bar")

    def test_reluctant_positive_3(self):
        """ Test 'reluctant' lookahead mode, positive check #3. """
        string = "fofofo"
        state = epp.State(string)
        parser = epp.chain(
            [epp.reluctant(epp.many(epp.literal("fo"), min_hits=1)),
             epp.literal("fo")])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, after = output
        self.assertIsNone(value)
        self.assertEqual(after.parsed, "fofo")
        self.assertEqual(after.left, "fo")


class TestEffects(unittest.TestCase):
    """ Test effects system. """

    def test_branch_positive(self):
        """ Test effects in branches, positive check. """
        string = "2"
        state = epp.State(string)
        parser = epp.branch(
            [epp.literal("1"),
             epp.chain([epp.literal("2"), epp.effect(lambda val, st: 2)])])
        output = epp.parse(None, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, 2)

    def test_effects_in_depth_negative(self):
        """
        Test effects that are not in the top level of a chain, negative check.
        """
        string = "123"
        state = epp.State(string)
        sign = epp.maybe(
            epp.chain(
                [
                    epp.literal("-"),
                    epp.effect(lambda val, st: -1)
                ]))
        parser = epp.chain(
            [
                sign,
                epp.integer(),
                epp.effect(lambda val, st: int(st.parsed) * val)
            ])
        output = epp.parse(1, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, 123)

    def test_effects_in_depth_positive(self):
        """
        Test effects that are not in the top level of a chain, positive check.
        """
        string = "-123"
        state = epp.State(string)
        sign = epp.maybe(
            epp.chain(
                [
                    epp.literal("-"),
                    epp.effect(lambda val, st: -1)
                ]))
        parser = epp.chain(
            [
                sign,
                epp.integer(),
                epp.effect(lambda val, st: int(st.parsed) * val)
            ])
        output = epp.parse(1, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, -123)

    def test_lookahead_1(self):
        """ Test effects interaction with lookahead, check #1. """
        string = "aaaaa"
        state = epp.State(string)
        elem = epp.chain([epp.literal("a"), epp.effect(lambda val, st: val + 1)])
        parser = epp.chain(
            [
                epp.greedy(epp.many(elem)),
                epp.literal("a"),
                epp.literal("a")
            ])
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, 3)

    def test_lookahead_2(self):
        """
        Test effects interaction with lookahead, check #2.

        This test checks if dropping effects from the chain on a lookahead
        retry works correctly.
        """
        string = "abaaa"
        state = epp.State(string)
        first = epp.effect(lambda val, st: val + 1)
        second = epp.effect(lambda val, st: val + 10)
        third = epp.effect(lambda val, st: val + 100)
        parser = epp.chain(
            [
                epp.greedy(epp.everything()),
                first,
                second,
                third,
                epp.literal("b")
            ])
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, 111)

    def test_many(self):
        """ Test 'many's interaction with effects. """
        string = "11111111"
        state = epp.State(string)
        elem = epp.chain([epp.literal("1"), epp.effect(lambda val, st: val + 1)])
        parser = epp.many(elem)
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, len(string))

    def test_monoeffect(self):
        """ Test an effect without a chain. """
        string = "foobar"
        state = epp.State(string)
        parser = epp.effect(lambda val, st: 10)
        output = epp.parse(0, state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, 10)

    def test_partial_application(self):
        """ Test partial application of effects in chains that support it. """
        string = "12345"
        state = epp.State(string)
        ef = epp.effect(lambda val, st: val + [st.parsed])
        parser = epp.chain(
            [
                epp.literal("1"), ef,
                epp.literal("2"), ef,
                epp.stop(),
                epp.literal("3"), ef,
                epp.literal("4"), ef,
                epp.literal("5"), ef
            ], all_or_nothing=False)
        output = epp.parse([], state, parser)
        self.assertIsNotNone(output)
        value, _ = output
        self.assertEqual(value, ["1", "2"])


class ExploratoryTesting(unittest.TestCase):
    """
    Exploratory tests.
    
    Test from here will migrate to other cases once the thing I've been trying
    is done (and fixed).
    """
    pass
    


if __name__ == "__main__":
    unittest.main()
