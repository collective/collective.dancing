import logging

import Acquisition
from plone.app.z3cform.interfaces import IPloneFormLayer
from plone.z3cform import z2
import stoneagehtml
import z3c.form.interfaces
from zope.interface import noLongerProvides
import zope.schema.vocabulary

import collective.singing.async

logger = logging.getLogger('collective.dancing')


def get_queue():
    """Get the job queue"""
    return collective.singing.async.get_queue('collective.dancing.jobs')

def get_request_container():
    site = zope.app.component.hooks.getSite()
    return site.aq_chain[-1]

def fix_request(wrapped, skip=1):
    return aq_append(wrapped, get_request_container(), skip)

def aq_append(wrapped, item, skip=0):
    """Return wrapped with an aq chain that includes `item` at the
    end.

      >>> class AQ(Acquisition.Explicit):
      ...     def __init__(self, name):
      ...         self.name = name
      ...     def __repr__(self):
      ...         return '<AQ %s>' % self.name

      >>> one, two, three = AQ('one'), AQ('two'), AQ('three')
      >>> one_of_two = one.__of__(two)
      >>> one_of_two.aq_chain
      [<AQ one>, <AQ two>]
      >>> aq_append(one_of_two, three).aq_chain
      [<AQ one>, <AQ two>, <AQ three>]
      >>> aq_append(one_of_two, three, skip=1).aq_chain
      [<AQ one>, <AQ three>]
    """
    value = item
    for item in tuple(reversed(wrapped.aq_chain))[skip:]:
        value = Acquisition.aq_base(item).__of__(value)
    return value

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


def compactify(html):
    """Make the html compact.

    We use stoneagehtml for this.  We catch at least one error that
    can occur with some css code, that stoneagehtml tries to clean up
    using cssutils.
    See https://bugs.launchpad.net/singing-dancing/+bug/410238

    We also return utf-8.
    """
    try:
        html = stoneagehtml.compactify(html, filter_tags=False)
    except IndexError:
        logger.warn("Exception while compacting html with stoneagehtml; "
                    "using original instead.")
        pass
    return html.decode('utf-8')


def switch_on(view, request_layer=z3c.form.interfaces.IFormLayer):
    # Fix the request. If we find a form layer from plone.app.z3cform take
    # it away. It uses a base template using context/main_template but our
    # views don't have an implicit Acquisition context. The base template
    # from plone.z3cform uses /@@standard-macros which does work, so we fall
    # back on that one
    z2.switch_on(view, request_layer=request_layer)
    request = view.request
    if IPloneFormLayer.providedBy(request):
        noLongerProvides(request, IPloneFormLayer)
