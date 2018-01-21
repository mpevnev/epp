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
            state_after = core.parse(string, parser)

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

    def test_integer_positive_1(self):
        """ Test 'integer' parser generator, positive check #1. """
        string = "123foo"
        state = core.State(string)
        parser = par.integer(False)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertIsNone(state_after.value)
        self.assertEqual(state.left, "foo")
        self.assertEqual(state.parsed, "123")

    def test_integer_positive_2(self):
        """ Test 'integer' parser generator, positive check #2. """
        string = "123foo"
        state = core.State(string)
        parser = par.integer(True)
        state_after = core.parse(state, parser)
        self.assertIsNotNone(state_after)
        self.assertEqual(state_after.value, 123)
        self.assertEqual(state.left, "foo")
        self.assertEqual(state.parsed, "123")

if __name__ == "__main__":
    unittest.main()
