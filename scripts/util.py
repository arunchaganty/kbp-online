#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

def unescape_sql(inp):
    if inp.startswith('"') and inp.endswith('"'):
        inp = inp[1:-1]
    return inp.replace('""','"').replace('\\\\','\\')

def parse_psql_array(inp):
    """
    Parses a postgres array.
    """
    inp = unescape_sql(inp)
    # Strip '{' and '}'
    if inp.startswith("{") and inp.endswith("}"):
        inp = inp[1:-1]

    lst = []
    elem = ""
    in_quotes, escaped = False, False

    for ch in inp:
        if escaped:
            elem += ch
            escaped = False
        elif ch == '"':
            in_quotes = not in_quotes
            escaped = False
        elif ch == '\\':
            escaped = True
        else:
            if in_quotes:
                elem += ch
            elif ch == ',':
                lst.append(elem)
                elem = ""
            else:
                elem += ch
            escaped = False
    if len(elem) > 0:
        lst.append(elem)
    return lst

def test_parse_psql_array():
    inp = '{Bond,was,set,at,$,"1,500",each,.}'
    lst = ["Bond", "was", "set", "at", "$", "1,500", "each","."]
    lst_ = parse_psql_array(inp)
    assert all([x == y for (x,y) in zip(lst, lst_)])

