from zope.interface import implements
from zope.component import queryUtility
from zope import component
from zope import interface
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from zope.app.pagetemplate import viewpagetemplatefile
from zope import schema
from zope.formlib import form

from plone.memoize.instance import memoize
from plone.memoize import ram
from plone.memoize.compress import xhtml_compress

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

import collective.singing
from collective.dancing import MessageFactory as _
from collective.dancing.browser.subscribe import SubscriptionAddForm
from collective.dancing.collector import ICollectorSchema
from collective.dancing import utils
 
class IChannelSubscribePortlet(IPortletDataProvider):
    """A portlet which renders the results of a collection object.
    """

    header = schema.TextLine(title=_(u"Portlet header"),
                             description=_(u"Title of the rendered portlet"),
                             required=True)
    channel = schema.Choice(title=_(u"The channel to enable subscriptions to."),
                            description=_(u"Find the channel you want to enable direct subscription to"),
                            required=True,
                            vocabulary='Channel Vocabulary'
                            )
    description = schema.TextLine(title=_(u"Portlet description"),
                           description=_(u"Description of the rendered portlet"),
                           required=True)
    show_options = schema.Bool(title=_(u"Set collector options"),
                            description=_(u"Click here to select collector options to be automatically enabled, when subscribing from this portlet."),
                            required=True,
                            default=True)
    
class Assignment(base.Assignment):
    """
    Portlet assignment.    
    This is what is actually managed through the portlets UI and associated
    with columns.
    """

    implements(IChannelSubscribePortlet)

    header = u""
    descriptions = False
    channel=None
    show_options = True

    def __init__(self, header=u"", description=u"", channel=None, show_options=True):
        self.header = header
        self.description = description
        self.channel = channel
        self.show_options = show_options

    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen. Here, we use the title that the user gave.
        """
        return self.header

    @property
    def all_channels(self):
        channels = queryUtility(collective.singing.interfaces.IChannelLookup)()
        if channels is None:
            return []
        return channels


class PortletSubscriptionAddForm(SubscriptionAddForm):
    """ """
    template = viewpagetemplatefile.ViewPageTemplateFile('titlelessform.pt')
    
class Renderer(base.Renderer):
    """Portlet renderer.
    
    This is registered in configure.zcml. The referenced page template is
    rendered, and the implicit variable 'view' will refer to an instance
    of this class. Other methods can be added and referenced in the template.
    """
    _template = ViewPageTemplateFile('channelsubscribe.pt')
    form_template = viewpagetemplatefile.ViewPageTemplateFile('titlelessform.pt')

    def __init__(self, *args):
        base.Renderer.__init__(self, *args)
        self.setup_form()

    def setup_form(self):
        collective.singing.z2.switch_on(self)
        if self.channel is not None:
            self.form = PortletSubscriptionAddForm(self.channel, self.request)
            #self.form.template = self.form_template
            self.form.format = 'html'
            self.form.update()
        
    render = _template

    @property
    def available(self):
        return bool(self.channel)

    @property
    def channel(self):
        channels = self.data.all_channels
        if channels is None:
            return channels
        for channel in channels:
            if channel.name == self.data.channel.name:
                return channel
        return channels[0]                 

    def channel_link(self):

        link = {'url':'%s/subscribe.html'%self.channel.absolute_url(),
                'title':self.channel.name}
        return link

    
class AddForm(base.AddForm):
    """Portlet add form.
    
    This is registered in configure.zcml. The form_fields variable tells
    zope.formlib which fields to display. The create() method actually
    constructs the assignment that is being added.
    """
    form_fields = form.Fields(IChannelSubscribePortlet)
    label = _(u"Add Channel Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter channel.")

    def create(self, data):
        return Assignment(**data)

    def update(self):
        super(AddForm, self).update()

class EditForm(base.EditForm):
    """Portlet edit form.
    
    This is registered with configure.zcml. The form_fields variable tells
    zope.formlib which fields to display.
    """
    form_fields = form.Fields(IChannelSubscribePortlet)
    label = _(u"Edit Channel Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter channel.")

#     def __call__(self):
#         self.form_fields = self.form_fields + \
#             form.Fields(schema.Bool(__name__='newbool',
#                                     title=_('New bool'),
#                                     description=_('New bool'),
#                                     default=False))
#         if not hasattr(self.context, 'newbool'):
#             self.context.newbool = False
#         self.update()
#         return self.render()

    def update(self):
        vocab = schema.vocabulary.SimpleVocabulary.fromValues(range(5))
        for channel in self.context.all_channels:
            if channel.collector is not None:
                collector_fields = form.Fields(channel.collector.schema,
                                               prefix='collector.%s'%channel.name)
                self.form_fields += collector_fields
                for field in collector_fields:
                    if not hasattr(self.context, field.__name__):
                        setattr(self.context, field.__name__, False)
        super(EditForm, self).update()

@component.adapter(Assignment)
@interface.implementer(collective.dancing.collector.ICollectorSchema)
def collectordata_from_assignment(assignment):
    collector_data = collective.singing.interfaces.ICollectorData(assignment)
    return utils.AttributeToDictProxy(collector_data)
