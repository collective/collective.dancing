import zope.schema.vocabulary
import z3c.form.interfaces
import Acquisition

class AttributeToDictProxy(object):
    def __init__(self, wrapped, default=z3c.form.interfaces.NOVALUE):
        super(AttributeToDictProxy, self).__setattr__('wrapped', wrapped)
        super(AttributeToDictProxy, self).__setattr__('default', default)

    def __setitem__(self, name, value):
        self.wrapped[name] = value

    __setattr__ = __setitem__

    def __getattr__(self, name):
        return self.wrapped.get(name, self.default)

class LaxVocabulary(zope.schema.vocabulary.SimpleVocabulary):
    """This vocabulary treats values the same if they're equal.
    """
    def getTerm(self, value):
        same = [t for t in self if t.value == Acquisition.aq_base(value)]
        if same:
            return same[0]
        else:
            raise LookupError(value)

def fixAcquisitionChain(req, chain):
    """Return object with proper aq context."""

    for item in reversed(chain):
        req = Acquisition.aq_base(item).__of__(req)
        
    return req        
