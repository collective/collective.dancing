import OFS

from zope import interface
from zope import component
#from zope import schema
import zope.annotation.interfaces
#from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
import zope.app.component.hooks
#import zope.sendmail.interfaces
import Products.CMFCore.interfaces
import Products.CMFPlone.interfaces
import collective.singing.interfaces
#import collective.singing.mail

from collective.dancing import MessageFactory as _
from collective.dancing import utils

class TemplateContainer(OFS.Folder.Folder):
    Title = u"Templates"

@component.adapter(TemplateContainer,
                   zope.app.container.interfaces.IObjectAddedEvent)
def container_added(container, event):
    name = 'default-template'

class Template(OFS.SimpleItem.SimpleItem):

    interface.implements(collective.singing.interfaces.ITemplate)

    def __init__(self, name, title=None):
        self.name = name
        if title is None:
            title = name
        self.title = title
        super(Template, self).__init__(name)

    @property
    def id(self):
        return self.name

    def Title(self):
        return self.title

    def __call__(self, options):
        pass
    
def template_lookup():
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return root['portal_newsletters']['templates'].objectValues()
interface.directlyProvides(template_lookup,
                           collective.singing.interfaces.ITemplateLookup)
