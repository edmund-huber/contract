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
        self.assertRaisesRegexp(FailedContract, r'^expected type str, got type int$', exclaim, 5)

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
        self.assertRaisesRegexp(FailedContract, r'^expected type str, got type int$', prepender, 5)
        self.assertRaisesRegexp(FailedContract, r'^expected type str, got type int$', prepender('hello, '), 5)

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
        self.assertRaisesRegexp(FailedContract, r'^expected a 1-ple, got a 0-ple$', i_give_you_happy) # TODO: this could be a more useful message.
        self.assertRaisesRegexp(FailedContract, r'^expected method, got str$', i_give_you_happy, 'joy joy')
        self.assertRaisesRegexp(FailedContract, r'^expected a contract-wrapped method$', i_give_you_happy, lambda s: s)

    def test_unit(self):
        @contract('() -> int')
        def f():
            return 42
        # this is ok
        self.assertEqual(f(), 42)
        # these are not ok
        self.assertRaisesRegexp(FailedContract, r'^expected the empty tuple, got \(\)$', f, ()) # TODO, heh
        self.assertRaisesRegexp(FailedContract, r'^expected the empty tuple, got \(5,\)$', f, (5,))

    def test_class(self):
        class C(object):
            pass
        @contract('(C,) -> int')
        def f(c):
            return 42
        # this is ok
        self.assertEqual(f(C()), 42)
        # these are not ok
        self.assertRaisesRegexp(FailedContract, r'^expected type C, got type type$', f, C)
        self.assertRaisesRegexp(FailedContract, r'^expected type C, got type int$', f, 42)
        self.assertRaisesRegexp(FailedContract, r'^expected type C, got type type$',  f, object)
        self.assertRaisesRegexp(FailedContract, r'^expected type C, got type object$',  f, object())

    def test_nested_unit(self):
        @contract('(((),),) -> str')
        def f(unit_unit):
            return 'hello'
        # this is ok
        self.assertEqual(f((())), 'hello')
        # these are not ok
        # ..

    def test_list_of_int(self):
        @contract('[int] -> str')
        def f(l):
            return ','.join([str(i) for i in l])
        # this is ok
        self.assertEqual(f([1, 2, 3]), '1,2,3')
        # these are not ok
        # ..

    def test_list_of_list_of_int(self):
        @contract('[[int]] -> str')
        def f(l_o_l):
            return ';'.join([','.join([str(i) for i in l]) for l in l_o_l])
        # this is ok
        self.assertEqual(f([[1, 2, 3], [4, 5, 6]]), '1,2,3;4,5,6')
        # these are not ok
        # ..

    def test_set_of_int(self):
        @contract('{int} -> int')
        def f(s):
            return len(s)
        # this is ok
        self.assertEqual(f(set([1, 2, 3])), 3)
        # these are not ok
        # ..

    def test_list_of_set_of_int(self):
        @contract('[{int}] -> [int]')
        def f(l_o_s):
            return [len(s) for s in l_o_s]
        # this is ok
        self.assertEqual(f([set([1, 2, 3]), set([4, 5]), set([1])]), [3, 2, 1])
        # these are not ok
        # ..

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
