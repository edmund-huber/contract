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
        self.assertRaises(FailedContract, exclaim, 5)

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
        self.assertRaises(FailedContract, prepender, 5)
        self.assertRaises(FailedContract, prepender('hello, '), 5)

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
