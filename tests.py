from contract import contract, InvalidContract, FailedContract
import unittest

class TestContracts(unittest.TestCase):
    
    def test_str_to_str(self):
        @contract('(str,) -> str')
        def exclaim(s):
            return s + '!'
        # this is ok
        self.assertEqual(exclaim('hello'), 'hello!')
        # this is not ok
        self.assertRaisesRegexp(FailedContract, '^expected type str, got type int$', exclaim, 5)

    def test_str_to_str_to_str(self):
        @contract('(str,) -> (str,) -> str')
        def prepender(s):
            @contract('(str,) -> str')
            def wrapper(s2):
                return s + s2
            return wrapper
        # this is ok
        self.assertEqual(prepender('hello, ')('dave'), 'hello, dave')
        # these are not ok
        self.assertRaisesRegexp(FailedContract, '^expected type str, got type int$', prepender, 5)
        self.assertRaisesRegexp(FailedContract, '^expected type str, got type int$', prepender('hello, '), 5)

    def test_argle_bargle(self):
        @contract('((str,) -> str,) -> str')
        def i_give_you_happy(f):
            return f('happy')
        @contract('(str,) -> str')
        def joy_joy(s):
            return s + ' ' + s + ' joy joy'
        # this is ok
        self.assertEqual(i_give_you_happy(joy_joy), 'happy happy joy joy')
        # these are not ok
        self.assertRaisesRegexp(FailedContract, '^expected a 1-ple, got a 0-ple$', i_give_you_happy) # TODO: this could be a more useful message.
        self.assertRaisesRegexp(FailedContract, '^expected method, got str$', i_give_you_happy, 'joy joy')
        self.assertRaisesRegexp(FailedContract, '^expected a contract-wrapped method$', i_give_you_happy, lambda s: s)

    def test_invalid_contracts(self):
        # that's just not a valid type.
        with self.assertRaises(InvalidContract):
            @contract('->')
            def f():
                pass
        # this isn't a function type.
        with self.assertRaises(InvalidContract):
            @contract('str')
            def f():
                pass

if __name__ == '__main__':
    unittest.main()
