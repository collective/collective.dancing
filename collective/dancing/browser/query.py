from zope import interface
from zope import schema

from plone.app.z3cform.queryselect import ArchetypesContentSourceBinder
from plone.app.z3cform.queryselect import uid2wref

from collective.dancing import MessageFactory as _

class IReferenceSelection(interface.Interface):
    items = schema.Set(
        title=_(u"Items"),
        description=_(u"Enter a search query to find content."),
        value_type=schema.Choice(source=ArchetypesContentSourceBinder())
        )

ReferenceSelection = uid2wref(IReferenceSelection['items'])
