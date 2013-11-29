import re

try:
    import termcolor
except:
    pass

def red(s, try_termcolor=False):
    if try_termcolor:
        try:
            return termcolor.colored(s, 'red')
        except:
            pass
    return '>>%s<<' % s

class InvalidContract(Exception):
    pass

class AmbiguousContract(Exception):
    pass

class InternalFailedContract(Exception):
    pass

class FailedContract(Exception):
    pass

class InternalContractError(Exception):
    pass

t_type = ('type', r'[A-Za-z]+')
t_arrow = ('arrow', r'->')
t_lparen = ('lparen', r'\(')
t_rparen = ('rparen', r'\)')
t_comma = ('comma', r',')
t_lbrack = ('lbrack', r'\[')
t_rbrack = ('rbrack', r'\]')
t_lbrace = ('lbrace', r'{')
t_rbrace = ('rbrace', r'}')
t_colon = ('colon', r':')
t_question = ('question', r'\?')

root = 'fun'
rules = [
    ('fun', ('fixed_tup', t_arrow, 'typ')),

    ('fixed_tup', (t_lparen, t_rparen)),
    ('fixed_tup', (t_lparen, 'typ', t_comma, t_rparen)),
    ('fixed_tup', (t_lparen, 'typ', t_comma, 'typ', 'more_fixed_tup', t_rparen)),
    ('more_fixed_tup', (t_comma, 'typ', 'more_fixed_tup')),
    ('more_fixed_tup', ()),

    ('list', (t_lbrack, 'typ', t_rbrack)),

    ('set', (t_lbrace, 'typ', t_rbrace)),

    ('dict', ('typ', t_colon, 'typ')),

    ('t', ('fixed_tup',)),
    ('t', ('list',)),
    ('t', ('set',)),
    ('t', ('dict',)),
    ('t', (t_type,)),
    ('t', (t_lparen, 'typ', t_rparen)),
    ('t', ('fun',)),
    # either nullable, or not.
    ('typ', ('t', t_question)),
    ('typ', ('t',)),
    ]

def rule_matcher(rule, lhs, *rhs):
    if rule['lhs'] == lhs:
        if len(rule['rhs']) == len(rhs):
            for rhs_1, rhs_2 in zip(rhs, rule['rhs']):
                if type(rhs_1) == tuple:
                    if rhs_2.get('term') != rhs_1[0]:
                        return False
                elif type(rhs_1) == str:
                    if rhs_2.get('lhs') != rhs_1:
                        return False
                else:
                    assert False
            return True
    return False

def earley(s):
    # initialize chart
    chart = [[] for _ in range(len(s) + 1)]
    for r_lhs, r_rhs in rules:
        if r_lhs == root:
            chart[0].append({
                    'begin': 0,
                    'lhs': r_lhs,
                    'uncompleted_rhs': tuple(r_rhs),
                    'rhs': (),
                    'span': ''
                    })
    # fill in each column
    for i in range(len(chart)):
        while True:
            new_states = list(chart[i])
            for state in chart[i]:
                # predict?
                if state['uncompleted_rhs']:
                    for r_lhs, r_rhs in rules:
                        if state['uncompleted_rhs'][0] == r_lhs: # this only works because of the tuple-wrapping for terms.
                            new_state = {
                                'begin': i,
                                'lhs': r_lhs,
                                'uncompleted_rhs': tuple(r_rhs),
                                'rhs': (),
                                'span': ''
                                }
                            if new_state not in new_states:
                                new_states.append(new_state)
                # scan?
                if state['uncompleted_rhs'] and type(state['uncompleted_rhs'][0]) is tuple:
                    term, term_re = state['uncompleted_rhs'][0]
                    m = re.match(term_re, s[i:])
                    if m:
                        new_state = {
                            'begin': state['begin'],
                            'lhs': state['lhs'],
                            'uncompleted_rhs': state['uncompleted_rhs'][1:],
                            'rhs': state['rhs'] + ({'term': term, 'token': m.group(0)},),
                            'span': state['span'] + m.group(0)
                            }
                        chart[i + len(m.group(0))].append(new_state)
                # complete?
                if not state['uncompleted_rhs']:
                    for previous_state in chart[state['begin']]:
                        if previous_state['uncompleted_rhs'] and previous_state['uncompleted_rhs'][0] == state['lhs']:
                            new_state = {
                                'begin': previous_state['begin'],
                                'lhs': previous_state['lhs'],
                                'uncompleted_rhs': tuple(previous_state['uncompleted_rhs'][1:]),
                                'rhs': previous_state['rhs'] + (state,),
                                'span': previous_state['span'] + state['span']
                                }
                            if new_state not in new_states:
                                new_states.append(new_state)
            # process this set of states again if it's gotten bigger.
            if len(new_states) > len(chart[i]):
                chart[i] = new_states
            else:
                break
    # return the last column of states after we pretty it up a bit.
    complete = filter(lambda state: state['begin'] == 0 and not state['uncompleted_rhs'] and state['lhs'] == root, chart[-1])
    def pretty(state):
        if 'term' in state:
            return {'term': state['term'], 'token': state['token']}
        else:
            return {'lhs': state['lhs'], 'rhs': tuple(pretty(rhs) for rhs in state['rhs']), 'span': state['span']}
    return map(pretty, complete)

def check_value(schema, value):
    # fun
    if rule_matcher(schema, 'fun', 'fixed_tup', t_arrow, 'typ'):
        expected_contract = '%s->%s' % (schema['rhs'][0]['span'], schema['rhs'][2]['span'])
        if type(value).__name__ == 'function':
            if getattr(value, '__contract__', None) is not None:
                # this is so horrible, i am a horrible
                if value.__contract__ != expected_contract:
                    raise InternalFailedContract(expected_contract, red(value.__contract__))
            else:
                raise InvalidContract('expected a contract-wrapped method') #maybe??????
        else:
            raise InternalFailedContract(expected_contract, red(type(value).__name__))

    # t
    elif rule_matcher(schema, 't', 'fixed_tup'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 't', 'list'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 't', 'set'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 't', 'dict'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 't', t_type):
        expect_type = schema['rhs'][0]['token']
        if expect_type != type(value).__name__:
            raise InternalFailedContract(expect_type, red(type(value).__name__))
    elif rule_matcher(schema, 't', t_lparen, 'typ', t_rparen):
        check_value(schema['rhs'][1], value)
    elif rule_matcher(schema, 't', 'fun'):
        check_value(schema['rhs'][0], value)

    # typ
    elif rule_matcher(schema, 'typ', 't'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 'typ', 't', t_question):
        if value is not None:
            check_value(schema['rhs'][0], value)

    # list
    elif rule_matcher(schema, 'list', t_lbrack, 'typ', t_rbrack):
        if type(value) == list:
            for v in value:
                try:
                    check_value(schema['rhs'][1], v)
                except InternalFailedContract, e:
                    # unlike tuples, shortcircuit, because lists are supposed to be homogenous.
                    raise InternalFailedContract(schema['span'], '[..' + red(e.args[1]) + '..]')
        else:
            raise InternalFailedContract(schema['span'], red(type(value).__name__))

    # set
    elif rule_matcher(schema, 'set', t_lbrace, 'typ', t_rbrace):
        if type(value) == set:
            for v in value:
                try:
                    check_value(schema['rhs'][1], v)
                except InternalFailedContract, e:
                    # just like for lists, we shortcircuit, because sets are homogenous.
                    raise InternalFailedContract(schema['span'], '{..' + red(e.args[1]) + '..}')
        else:
            raise InternalFailedContract(schema['span'], red(type(value).__name__))

    # dict
    elif rule_matcher(schema, 'dict', 'typ', t_colon, 'typ'):
        if type(value) == dict:
            for k, v in value.iteritems():
                is_okay = True
                key_span = schema['rhs'][0]['span']
                value_span = schema['rhs'][2]['span']
                try:
                    check_value(schema['rhs'][0], k)
                except InternalFailedContract, e:
                    # " " " dicts are homogenous.
                    key_span = red(e.args[1])
                    is_okay = False
                try:
                    check_value(schema['rhs'][2], v)
                except InternalFailedContract, e:
                    value_span = red(e.args[1])
                    is_okay = False
                if not is_okay:
                    raise InternalFailedContract(schema['span'], '{..' + key_span + ':' + value_span + '..}')
        else:
            raise InternalFailedContract(schema['span'], red(type(value).__name__))

    # tuple
    elif rule_matcher(schema, 'fixed_tup', t_lparen, t_rparen):
        if value != ():
            raise InternalFailedContract(schema['span'], type(value).__name__)
    elif rule_matcher(schema, 'fixed_tup', t_lparen, 'typ', t_comma, t_rparen):
        try:
            value[0]
        except IndexError:
            raise InternalFailedContract(schema['span'], '(_,)')
        try:
            check_value(schema['rhs'][1], value[0])
        except InternalFailedContract, e:
            raise InternalFailedContract(schema['span'], '(' + red(e.args[1]) + ',)')
    elif rule_matcher(schema, 'fixed_tup', t_lparen, 'typ', t_comma, 'typ', 'more_fixed_tup', t_rparen):
        expected = [schema['rhs'][1], schema['rhs'][3]]
        p = schema['rhs'][4]
        while True:
            if rule_matcher(p, 'more_fixed_tup', t_comma, 'typ', 'more_fixed_tup'):
                expected.append(p['rhs'][1])
                p = p['rhs'][2]
            elif rule_matcher(p, 'more_fixed_tup'):
                break
            else:
                raise InternalContractError('the parsetree is fucked right here')
        if type(value) != tuple:
            raise InternalFailedContract(schema['span'], type(value).__name__)
        if len(value) != len(expected):
            raise InternalFailedContract(schema['span'], '(' + ('_,' * len(value)) + ')')
        # complicated error reporting follows
        matches = True
        discovered = []
        for e, v in zip(expected, value):
            try:
                check_value(e, v)
            except InternalFailedContract, e:
                discovered.append(e.args[1])
                matches = False
            else:
                discovered.append(e['span'])
        if not matches:
            raise InternalFailedContract(schema['span'], '(' + ','.join(discovered) + ',)')

    # we're fucked!
    else:
        import pprint
        raise InternalContractError('check_value() is incompletely defined (no case for %s)!' % pprint.PrettyPrinter().pformat(schema))

def contract(s, debug=False, show_line=True):
    # parse it.
    s = s.translate(None, ' \t\n')
    exprs = earley(s)
    if debug:
        import pprint
        pprint.PrettyPrinter().pprint(exprs)
    if len(exprs) == 0:
        raise InvalidContract('contract could not be parsed!')
    if len(exprs) > 1:
        import pprint
        for e in exprs:
            print pprint.PrettyPrinter().pformat(e)
        raise AmbiguousContract('contract is not unambiguous!')
    parse = exprs[0]
    # here's the wrapper that enforces the contract.
    def wrapped(f):
        where = '%s L%i' % (f.func_code.co_filename, f.func_code.co_firstlineno)
        def inner(*args):
            # check the input..
            try:
                check_value(parse['rhs'][0], args)
            except InternalFailedContract, e:
                if show_line:
                    raise FailedContract('%s: expected input is %s, but got %s' % (where, e.args[0], e.args[1]))
                else:
                    raise FailedContract('expected input is %s, but got %s' % (e.args[0], e.args[1]))
            # Now check the output. We do input and output checking
            # separately, because we don't want to run the inner
            # method with input which we know is wrong.
            output = f(*args)
            try:
                check_value(parse['rhs'][2], output)
            except InternalFailedContract, e:
                if show_line:
                    raise FailedContract('%s: expected output is %s, but got %s' % (where, e.args[0], e.args[1]))
                else:
                    raise FailedContract('expected output is %s, but got %s' % (e.args[0], e.args[1]))
            # if it got this far, we're good.
            return output
        # this is horrible, there needs to be some enforcement of a canonical form for this to really work
        inner.__contract__ = s
        return inner
    return wrapped

