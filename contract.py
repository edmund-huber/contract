# continuation:    str -> @
# at some point.

import re

t_type = ('type', r'[A-Za-z]+')
t_arrow = ('arrow', r'->')
t_lparen = ('lparen', r'\(')
t_rparen = ('rparen', r'\)')

rules = [
    ('typ', (t_type,)),
    ('typ', (t_lparen, 'typ', t_rparen)),
    ('typ', ('typ', t_arrow, 'typ')),
    ]

def earley(s):
    # initialize chart
    chart = [[] for _ in range(len(s) + 1)]
    for r_lhs, r_rhs in rules:
        chart[0].append({
                'begin': 0,
                'lhs': r_lhs,
                'uncompleted_rhs': tuple(r_rhs),
                'rhs': ()
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
                                'rhs': ()
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
                            'rhs': state['rhs'] + ({'term': term, 'token': m.group(0)},)
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
                                'rhs': previous_state['rhs'] + (state,)
                                }
                            if new_state not in new_states:
                                new_states.append(new_state)
            if len(new_states) > len(chart[i]):
                chart[i] = new_states
            else:
                break
    complete = filter(lambda state: state['begin'] == 0 and not state['uncompleted_rhs'], chart[-1])
    def pretty(state):
        if 'term' in state:
            return {'term': state['term'], 'token': state['token']}
        else:
            return {'lhs': state['lhs'], 'rhs': tuple(pretty(rhs) for rhs in state['rhs'])}
    return map(pretty, complete)

def contract(s, debug=False):
    exprs = earley(s.translate(None, ' \t\n'))
    assert len(exprs) > 0, 'contract could not be parsed!'
    assert len(exprs) == 1, 'contract is not unambiguous!'
    assert exprs[0]['lhs'] == 'typ', 'contract is invalid!'
    if debug:
        import pprint
        pprint.PrettyPrinter().pprint(exprs)
    def wrapped(f):
        return f
    return wrapped

#@contract("->") # cannot be parsed.
def invalid():
    return None

#@contract("str") # is not a function type..
def invalid():
    return None

#@contract("str -> str -> str") # has more than one interpretation: (str -> str) -> str , or str -> (str -> str)
def invalid():
    return None

@contract("str  -> str", debug=True)
def exclaim(s):
    return s + "!"

@contract("str -> (str -> str)", debug=True)
def string_adder(s):
    return lambda s2: s2 + s

#@contract("int -> int?")
def nonzero(i):
    if i == 0:
        None
    else:
        return i

