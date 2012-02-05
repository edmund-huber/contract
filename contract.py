import re

class InvalidContract(Exception):
    pass

class AmbiguousContract(Exception):
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

root = 'fun'
rules = [
    ('fun', ('fixed_tup', t_arrow, 'typ')),

    ('fixed_tup', (t_lparen, t_rparen)),
    ('fixed_tup', (t_lparen, 'typ', t_comma, 'more_fixed_tup', t_rparen)),
    ('more_fixed_tup', ()),
    ('more_fixed_tup', ('typ', 'more_fixed_tup')),

    ('typ', ('fixed_tup',)),
    ('typ', (t_type,)),
    ('typ', (t_lparen, 'typ', t_rparen)),
    ('typ', ('fun',))
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
    # return the last column after we pretty it up a bit.
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
        if type(value).__name__ == 'function':
            if getattr(value, '__contract__', None) is not None:
                # this is so horrible, i am a horrible
                expected_contract = '%s->%s' % (schema['rhs'][0]['span'], schema['rhs'][2]['span'])
                if value.__contract__ != expected_contract:
                    raise FailedContract('the contract is %s, we wanted %s' % (value.__contract__, expected_contract))
            else:
                raise FailedContract('expected a contract-wrapped function')
        else:
            raise FailedContract('expected function, got %s' % type(value))

    # typ
    elif rule_matcher(schema, 'typ', 'fixed_tup'):
        check_value(schema['rhs'][0], value)
    elif rule_matcher(schema, 'typ', t_type):
        expect_type = schema['rhs'][0]['token']
        if expect_type != type(value).__name__:
            raise FailedContract('expected type %s, got type %s' % (expect_type, type(value)))
    elif rule_matcher(schema, 'typ', t_lparen, 'typ', t_rparen):
        check_value(schema['rhs'][1], value)
    elif rule_matcher(schema, 'typ', 'fun'):
        check_value(schema['rhs'][0], value)

    # fixed_tup, more_fixed_tup
    elif rule_matcher(schema, 'fixed_tup', t_lparen, t_rparen):
        if value != ():
            raise FailedContract('expected the empty tuple, got %s' % value)
    elif rule_matcher(schema, 'fixed_tup', t_lparen, 'typ', t_comma, 'more_fixed_tup', t_rparen):
        check_value(schema['rhs'][1], value[0])
        i = 1
        p = schema['rhs'][3]
        while True:
            if rule_matcher(p, 'more_fixed_tup'):
                break
            elif rule_matcher(p, 'more_fixed_tup', 'typ', 'more_fixed_tup'):
                check_value(p['rhs'][0], value[i])
                i += 1
                p = p['rhs'][1]
            else:
                raise InternalContractError('the parsetree is fucked right here')

    # we're fucked!
    else:
        import pprint
        raise InternalContractError('check_value() is incompletely defined (no case for %s)!' % pprint.PrettyPrinter().pformat(schema))

def contract(s, debug=False):
    # parse it.
    s = s.translate(None, ' \t\n')
    exprs = earley(s)
    if debug:
        import pprint
        pprint.PrettyPrinter().pprint(exprs)
    if len(exprs) == 0:
        raise InvalidContract('contract could not be parsed!')
    if len(exprs) > 1:
        raise AmbiguousContract('contract is not unambiguous!')
    parse = exprs[0]
    # here's the wrapper that enforces the contract.
    def wrapped(f):
        def inner(*args):
            # check the input..
            check_value(parse['rhs'][0], args)
            # check the output..
            output = f(*args)
            check_value(parse['rhs'][2], output)
            # if it got this far, we're good.
            return output
        # this is horrible, there needs to be some enforcement of a canonical form for this to really work
        inner.__contract__ = s
        return inner
    return wrapped

