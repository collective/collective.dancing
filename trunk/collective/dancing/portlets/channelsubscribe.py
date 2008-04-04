from Acquisition import aq_parent, aq_inner
from zope import component
from zope import event
from zope import lifecycleevent
from zope import interface
from zope import publisher  
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from zope.app.pagetemplate import viewpagetemplatefile
from zope import schema
from zope.formlib import form

from Products.Five import BrowserView
import z3c.form

from plone.memoize.instance import memoize
from plone.memoize import ram
from plone.memoize.compress import xhtml_compress

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

import collective.singing
from collective.dancing import MessageFactory as _
from collective.dancing.browser.subscribe import SubscriptionAddForm
from collective.dancing.collector import ICollectorSchema
from collective.dancing import utils

test_vocab = schema.vocabulary.SimpleVocabulary.fromValues(range(5))
 
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
    test = schema.Set(title=u"Test",
                      description=u"Just to see how sets are stored on the assignment",
                      value_type=schema.Choice(vocabulary=test_vocab))

class Assignment(base.Assignment):
    """
    Portlet assignment.    
    This is what is actually managed through the portlets UI and associated
    with columns.
    """
    interface.implements(IChannelSubscribePortlet, ICollectorSchema)
    header = u""
    descriptions = False
    channel=None
    show_options = True

    def __init__(self,
                 header=u"",
                 description=u"",
                 channel=None,
                 show_options=True,
                 test=None):
        self.header = header
        self.description = description
        self.channel = channel
        self.show_options = show_options
        self.test = test
        self.selected_collectors = []
    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen. Here, we use the title that the user gave.
        """
        return self.header

    @property
    def all_channels(self):
        channels = component.queryUtility(collective.singing.interfaces.IChannelLookup)()
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

def prefix(self):
    return str(self.__class__.__name__ + '-'.join(self.context.getPhysicalPath()))


class EditCollectorOptionsForm(z3c.form.subform.EditSubForm):
    """Edit a single collectors options."""
    template = viewpagetemplatefile.ViewPageTemplateFile(
        '../browser/subform.pt')

    css_class = 'subForm subForm-level-1'
    ignoreContext = False

    @property
    def ignoreRequest(self):
        return not self.selected_channel
    
    prefix = property(prefix)
    
    def __init__(self, context, request, channel, parentForm):
        self.context = context
        self.request = request
        self.channel = channel
        self.parentForm = self.__parent__ = parentForm
        self.heading = 'Options for %s'%channel.Title()
        self.collector_schema = channel.collector.schema
        #interface.directlyProvides(context, self.collector_schema)
        #XXX:  Is this a memory leak?
        @component.adapter(Assignment)
        @interface.implementer(self.collector_schema)
        def hack_for_dynamic_interface(assignment):
            return assignment
        component.provideAdapter(hack_for_dynamic_interface)
        
    @property
    def fields(self):
        return z3c.form.field.Fields(self.collector_schema)

    @property
    def label(self):
        return _(u"${channel} options", mapping={'channel':self.channel.Title()})

    @property
    def selected_channel(self):
        return self.context == self.parentForm.context.channel

    
class ChannelSubscribePortletEditForm(z3c.form.form.EditForm):
    """  """
    template = viewpagetemplatefile.ViewPageTemplateFile('../browser/form-with-subforms.pt')
    fields = z3c.form.field.Fields(IChannelSubscribePortlet)

    css_class = 'editForm portletEditForm'
    heading = _(u"Edit Channel Subscribe Portlet")

    def update(self):
        super(ChannelSubscribePortletEditForm, self).update()
        self.subforms = []
        for channel in self.context.all_channels:
            if channel.collector is not None:
                option_form = EditCollectorOptionsForm(self.context,
                                                       self.request,
                                                       channel,
                                                       self)
                option_form.update()
                self.subforms.append(option_form)
        

class ChannelSubscribePortletView(BrowserView):
    __call__ = ViewPageTemplateFile('z3c.plone.portlet.pt')

    def referer(self):
        return self.request.get('referer', '')

    # eventually replace this with a referer and redirect like regular
    # plone portlets.
    # NB: this would require combining status messages from subforms.
    def back_link(self):
        url = self.request.form.get('referer')
        if not url:
            addview = aq_parent(aq_inner(self.context))
            context = aq_parent(aq_inner(addview))
            url = str(component.getMultiAdapter((context, self.request),
                        name=u"absolute_url")) + '/@@manage-portlets'
        return dict(url=url,
                    label=_(u"Back to portlets"))


class ChannelSubscribePortletEditView(ChannelSubscribePortletView):

    label = _(u"Edit Channel Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter channel.")

    def contents(self):
        collective.singing.z2.switch_on(self)
        return ChannelSubscribePortletEditForm(self.context, self.request)()


class EditCollectorOptionsAddForm(z3c.form.form.Form):
    """Edit a single collectors options.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile(
        '../browser/subform.pt')

    css_class = 'subForm subForm-level-1'
    ignoreContext = True    
    prefix = property(prefix)
    
    def __init__(self, context, request, channel, parentForm):
        super(EditCollectorOptionsAddForm, self).__init__(context, request)
        self.context = context
        self.request = request
        self.channel = channel
        self.parentForm = self.__parent__ = parentForm
        self.heading = 'Options for %s'%channel.Title()
    
    @property
    def fields(self):
        return z3c.form.field.Fields(self.channel.collector.schema)

    @property
    def label(self):
        return _(u"${channel} options", mapping={'channel':self.channel.Title()})

    @property
    def selected_channel(self):
        return self.context == self.parentForm.context.channel

    
class ChannelSubscribePortletAddForm(z3c.form.form.AddForm):
    """ """
    template = viewpagetemplatefile.ViewPageTemplateFile('../browser/form-with-subforms.pt')
    fields = z3c.form.field.Fields(IChannelSubscribePortlet)

    css_class = 'addForm portletAddForm'
    heading = _(u"Add Channel Subscribe Portlet")

    subforms = []

    def __init__(self, context, request):
        super(ChannelSubscribePortletAddForm, self).__init__(context, request)
        self.update_subforms()
    
    def create(self, data):
        return Assignment(**data)

    def add(self, object):
        self.context.add(object)

    def nextURL(self):
        #XXX: this should be computed
        return '../../@@manage-portlets'
        
    def update_subforms(self):
        channels = component.queryUtility(collective.singing.interfaces.IChannelLookup)()
        if channels is not None:
            for channel in channels:
                if channel.collector is not None:
                    option_form = EditCollectorOptionsAddForm(self.context,
                                                              self.request,
                                                              channel,
                                                              self)
                    option_form.update()
                    self.subforms.append(option_form)

     
class ChannelSubscribePortletAddView(ChannelSubscribePortletView):

    label = _(u"Add Channel Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter channel.")

    def contents(self):
        collective.singing.z2.switch_on(self)
        return ChannelSubscribePortletAddForm(self.context, self.request)()

