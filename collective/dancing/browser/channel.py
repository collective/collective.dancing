from zope import schema
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import field
from z3c.form import form
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone import utils

from collective.singing import z2
from collective.dancing import MessageFactory as _
from collective.dancing.channel import Channel
from collective.singing.browser import crud
from collective.singing.interfaces import IChannel

class ChannelManageForm(crud.CrudForm):
    """'Does everything' form for channels.
    """

    update_schema = field.Fields(IChannel).select('title')
    
    def get_items(self):
        return [(ob.getId(), ob) for ob in self.context.objectValues()]
    
    def add(self, data):
        name = utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        self.context[name] = Channel(name, data['title'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])
        
class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('skeleton.pt')
    
    label = _(u'Newsletter Channels administration')

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return ChannelManageForm(self.context, self.request)()
