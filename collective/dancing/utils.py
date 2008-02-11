import z3c.form.interfaces

class AttributeToDictProxy(object):
    def __init__(self, wrapped, default=z3c.form.interfaces.NOVALUE):
        self.wrapped = wrapped
        self.default = default

    def __setitem__(self, name, value):
        self.wrapped[name] = value

    def __getattr__(self, name):
        return self.wrapped.get(name, self.default)
