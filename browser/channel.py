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

class ChannelAddForm(form.AddForm):
    """Add form for channels.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    
    fields = field.Fields(schema.TextLine(__name__='title',
                                          title=_(u'Channel title')))

    def create(self, data):
        self._object_name = utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        return Channel(self.name)

    def add(self, object):
        self.context[object.id] = object

    def render(self):
        if self._finishedAdd:
            self.status = '"%s" created' % (self._object_name,)
        return super(form.AddForm, self).render()

class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('skeleton.pt')
    
    label = _(u'Newsletter Channels administration')

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return ChannelAddForm(self.context, self.request)()
