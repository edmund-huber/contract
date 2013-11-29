from contract import contract, InvalidContract, FailedContract, red
import functools
import unittest

contract = functools.partial(contract, show_line=False)
red = functools.partial(red, try_termcolor=False)

class BetterTestCase(unittest.TestCase):

    def assertRaisesString(self, e_class, e_message, f, *args, **kwargs):
        with self.assertRaises(e_class) as cm:
            f(*args, **kwargs)
        self.assertEqual(cm.exception.message, e_message)

class TestContracts(BetterTestCase):
    
    def test_str_to_str(self):
        @contract('(str,) -> str')
        def exclaim(s):
            return s + '!'
        # this is ok
        self.assertEqual(exclaim('hello'), 'hello!')
        # this is not ok
        self.assertRaisesString(FailedContract, 'expected input is (str,), but got (%s,)' % red(red('int')), exclaim, 5)

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
        self.assertRaisesString(FailedContract, 'expected input is (str,), but got (%s,)' % red(red('int')), prepender, 5)
        self.assertRaisesString(FailedContract, 'expected input is (str,), but got (%s,)' % red(red('int')), prepender('hello, '), 5)

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
        self.assertRaisesString(FailedContract, 'expected input is ((str,)->str,), but got (_,)', i_give_you_happy)
        self.assertRaisesString(FailedContract, 'expected input is ((str,)->str,), but got (%s,)' % red(red('str')), i_give_you_happy, 'joy joy')
        # I opine that this contract was never valid in the first
        # place. This is the only case that this exception should ever
        # be raised after a contract has been parsed.
        self.assertRaisesString(InvalidContract, 'expected a contract-wrapped method', i_give_you_happy, lambda s: s)

    def test_unit(self):
        @contract('() -> int')
        def f():
            return 42
        # this is ok
        self.assertEqual(f(), 42)
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is (), but got tuple', f, ()) # TODO, heh
        self.assertRaisesString(FailedContract, 'expected input is (), but got tuple', f, (5,))

    def test_class(self):
        class C(object):
            pass
        @contract('(C,) -> int')
        def f(c):
            return 42
        # this is ok
        self.assertEqual(f(C()), 42)
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is (C,), but got (%s,)' % red(red('type')), f, C)
        self.assertRaisesString(FailedContract, 'expected input is (C,), but got (%s,)' % red(red('int')), f, 42)
        self.assertRaisesString(FailedContract, 'expected input is (C,), but got (%s,)' % red(red('type')), f, object)
        self.assertRaisesString(FailedContract, 'expected input is (C,), but got (%s,)' % red(red('object')), f, object())

    def test_nested_unit(self):
        @contract('(((),),) -> str')
        def f(unit_unit):
            return 'hello'
        # this is ok
        self.assertEqual(f(((),)), 'hello')
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is (((),),), but got (%s,)' % red('(_,)'), f, ())
        self.assertRaisesString(FailedContract, 'expected input is (((),),), but got (>>(>>str<<,)<<,)', f, ('hi'))

    def test_list_of_int(self):
        @contract('([int],) -> str')
        def f(l):
            return ','.join([str(i) for i in l])
        # this is ok
        self.assertEqual(f([1, 2, 3]), '1,2,3')
        self.assertEqual(f([]), '')
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is ([int],), but got (>>>>NoneType<<<<,)', f, None)
        self.assertRaisesString(FailedContract, 'expected input is ([int],), but got (>>[..>>>>str<<<<..]<<,)', f, ['hi'])
        self.assertRaisesString(FailedContract, 'expected input is ([int],), but got (>>[..>>>>str<<<<..]<<,)', f, [42, 'hi'])

    def test_list_of_list_of_int(self):
        @contract('([[int]],) -> str')
        def f(l_o_l):
            return ';'.join([','.join([str(i) for i in l]) for l in l_o_l])
        # this is ok
        self.assertEqual(f([[1, 2, 3], [4, 5, 6]]), '1,2,3;4,5,6')
        self.assertEqual(f([[1, 2, 3]]), '1,2,3')
        self.assertEqual(f([[]]), '')
        self.assertEqual(f([]), '')
        # these are not ok 
        self.assertRaisesString(FailedContract, 'expected input is ([[int]],), but got (>>[..>>>>int<<<<..]<<,)', f, [1, 2, 3])
        self.assertRaisesString(FailedContract, 'expected input is ([[int]],), but got (>>[..>>[..>>>>str<<<<..]<<..]<<,)', f, [[], ['hi']])

    def test_set_of_int(self):
        @contract('({int},) -> int')
        def f(s):
            return len(s)
        # this is ok
        self.assertEqual(f(set([1, 2, 3])), 3)
        self.assertEqual(f(set()), 0)
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is ({int},), but got (%s,)' % red(red('list')), f, [1, 2, 3])
        self.assertRaisesString(FailedContract, 'expected input is ({int},), but got (%s,)' % red('{..%s..}' % red(red('str'))), f, set([1, 2, 'hi']))

    def test_list_of_set_of_int(self):
        @contract('([{int}],) -> [int]')
        def f(l_o_s):
            return [len(s) for s in l_o_s]
        # this is ok
        self.assertEqual(f([set([1, 2, 3]), set([4, 5]), set([1])]), [3, 2, 1])
        self.assertEqual(f([]), [])
        self.assertEqual(f([set()]), [0])
        # these are not ok
        self.assertRaisesString(FailedContract, 'expected input is ([{int}],), but got (%s,)' % red(red('set')), f, {1})
        self.assertRaisesString(FailedContract, 'expected input is ([{int}],), but got (>>[..>>>>int<<<<..]<<,)', f, [1, 2, 3])
        self.assertRaisesString(FailedContract, 'expected input is ([{int}],), but got (>>[..>>{..>>>>str<<<<..}<<..]<<,)', f, [set(), set(['hi'])])

    def test_dict(self):
        class C(object):
            pass
        @contract('(int:str, int) -> C')
        def f(m, i):
            return C()
        # this is ok
        self.assertEqual(type(f({5: 'hi'}, 5)), C)
        # this is not ok
        self.assertRaisesString(FailedContract, 'expected input is (int:str,int), but got ({..int:>>>>int<<<<..},int,)', f, {5: 10}, 5)
        self.assertRaisesString(FailedContract, 'expected input is (int:str,int), but got ({..>>>>str<<<<:str..},int,)', f, {'hello': 'hi'}, 5)
        self.assertRaisesString(FailedContract, 'expected input is (int:str,int), but got ({..>>>>str<<<<:>>>>int<<<<..},int,)', f, {'hello': 5}, 5)
        self.assertRaisesString(FailedContract, 'expected input is (int:str,int), but got ({..>>>>str<<<<:>>>>int<<<<..},>>str<<,)', f, {'hello': 5}, 'derp')
        self.assertRaisesString(FailedContract, 'expected input is (int:str,int), but got (int:str,>>str<<,)', f, {5: 'hello'}, 'derp')

    def test_nullable(self):
        @contract('(int?,) -> int')
        def f(i):
            if i is None:
                return 5
            else:
                return i * 2
        # ok
        self.assertEqual(f(None), 5)
        self.assertEqual(f(2), 4)
        # not ok
        self.assertRaisesString(FailedContract, 'expected input is (int?,), but got (%s,)' % red(red('str')), f, 'blargh')

    def test_nullable_dict(self):
        @contract('(int, int:(str?)) -> str')
        def f(i, m):
            return m[i] or 'bloop'
        # OK
        self.assertEqual(f(5, {5: 'z'}), 'z')
        self.assertEqual(f(5, {5: None}), 'bloop')
        # not ok
        self.assertRaisesString(FailedContract, 'expected input is (int,int:(str?)), but got (int,{..%s:(str?)..},)' % red(red('NoneType')), f, 5, {None: 'aaa'})

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

    def test_awesome_error_messages(self):
        @contract('([int],) -> str')
        def f(l_o_i):
            return 'aaaaaa'
        self.assertRaisesString(FailedContract, 'expected input is ([int],), but got (%s,)' % red(red('int')), f, 5)
        @contract('([int], [[str]]) -> str')
        def f(l_o_i, l_o_l_o_i):
            return 'aaaaaa'
        # ehhhhh
        #f([5, 'hehe'], [['derp', 'durp'], [4, 'lawl']])
        #self.assertRaisesString(FailedContract, 'expected input is ([int],[[str]]), but got ([..%s..],[..%s..],)' % (red('str'), red('[..int..]')),
        #                        f, [5, 'hehe'], [['derp', 'durp'], [4, 'lawl']])                      

if __name__ == '__main__':
    unittest.main()
