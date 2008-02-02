from z3c.form import field
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFPlone import utils
from collective.singing import z2
from collective.singing.browser import crud
from collective.singing.interfaces import IChannel

from collective.dancing import MessageFactory as _
from collective.dancing.channel import Channel
from collective.dancing.browser import controlpanel

class ManageChannelsForm(crud.CrudForm):
    """'Does everything' form for channels.
    """

    update_schema = field.Fields(IChannel).select('title')
    view_schema = field.Fields(IChannel).select('title')
    
    def get_items(self):
        return [(ob.getId(), ob) for ob in self.context.objectValues()]
    
    def add(self, data):
        name = utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        self.context[name] = Channel(name, data['title'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field, value):
        if field == 'title':
            return item.absolute_url()

class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')
    
    label = _(u'Newsletter Channels administration')
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return ManageChannelsForm(self.context.channels, self.request)()
