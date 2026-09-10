"""Minimal s-expression reader/writer for KiCad files."""
import re, uuid

class Sym(str): pass

_tok = re.compile(r'"(?:[^"\\]|\\.)*"|\(|\)|[^\s()]+')

def loads(text):
    toks = _tok.findall(text)
    pos = [0]
    def rd():
        t = toks[pos[0]]; pos[0] += 1
        if t == "(":
            out = []
            while toks[pos[0]] != ")":
                out.append(rd())
            pos[0] += 1
            return out
        if t.startswith('"'):
            return t[1:-1].replace('\\"', '"').replace('\\\\', '\\')
        return Sym(t)
    return rd()

def dumps(node, ind=0):
    pad = "\t" * ind
    if isinstance(node, list):
        if not node:
            return pad + "()"
        head = node[0]
        # keep short leaf forms on one line
        if all(not isinstance(c, list) for c in node) and len(node) <= 6:
            return pad + "(" + " ".join(_atom(c) for c in node) + ")"
        out = [pad + "(" + _atom(head)]
        for c in node[1:]:
            out.append(dumps(c, ind + 1) if isinstance(c, list)
                       else "\t" * (ind + 1) + _atom(c))
        out.append(pad + ")")
        return "\n".join(out)
    return pad + _atom(node)

def _atom(a):
    if isinstance(a, Sym): return str(a)
    if isinstance(a, bool): return "yes" if a else "no"
    if isinstance(a, float):
        s = ("%.6f" % a).rstrip("0").rstrip(".")
        return s if s not in ("", "-0") else "0"
    if isinstance(a, int): return str(a)
    return '"%s"' % str(a).replace("\\", "\\\\").replace('"', '\\"')

def find(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]

def first(node, name):
    f = find(node, name)
    return f[0] if f else None

def newuuid():
    return [Sym("uuid"), str(uuid.uuid4())]

def set_uuids(node):
    """Give every uuid in a subtree a fresh value."""
    if isinstance(node, list):
        if node and node[0] == "uuid" and len(node) == 2:
            node[1] = str(uuid.uuid4()); return
        for c in node: set_uuids(c)
