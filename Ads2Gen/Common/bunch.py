
from __future__ import print_function

from cStringIO import StringIO

NESTED = 'nested'
DOTTED = 'dotted'

__all__ = ["Bunch", NESTED, DOTTED]

class Bunch(dict):

    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ = self

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self.update(state)
        self.__dict__ = self

    def __str__(self):
        def vstr(v):
            if isinstance(v, Bunch):
                return '<Bunch(...%d...)>' % len(v.__dict__)
            else:
                repr(v)
        attr = ["%s=%s" % (a, vstr(v)) for (a, v) in self.__dict__.items()]
        return '<Bunch(' + " ".join(attr) + ')>'

    __repr__ = __str__

    def _dump_nested(self, writer, level=0):
        indent = "  " * level
        for k, v in self.items():
            if isinstance(v, Bunch):
                writer("%s%s = {" % (indent, k))
                v._dump_nested(writer, level=level + 1)
                writer("%s}" % indent)
            else:
                writer("%s%s = '%s';" % (indent, k, v))

    def _dump_dotted(self, writer, prefix=()):
        for k, v in self.items():
            if isinstance(v, Bunch):
                v._dump_dotted(writer, prefix=prefix + (k,))
            else:
                writer("%s = '%s';" % ('.'.join(prefix + (k,)), v))

    def dump(self, writer=print, mode=NESTED, name=None):
        if mode == NESTED:
            self._dump_nested(writer, level=0)
        else:
            if name:
                prefix = (name,)
            else:
                prefix = ()
            self._dump_dotted(writer, prefix=prefix)

    def dumps(self, mode=NESTED, name=None):
        s = StringIO()
        writer = lambda line: s.write(line + '\n')
        self.dump(writer=writer, mode=mode, name=name)
        return s.getvalue()

