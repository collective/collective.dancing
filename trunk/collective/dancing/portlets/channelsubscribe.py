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

    interface.implements(IChannelSubscribePortlet)

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

def prefix(self):
    return self.__class__.__name__ + '-'.join(self.context.getPhysicalPath())


class EditCollectorOptionsForm(z3c.form.subform.EditSubForm):
    """Edit a single collectors options.
    """

    template = viewpagetemplatefile.ViewPageTemplateFile(
        '../browser/subform.pt')

    css_class = 'subForm subForm-level-1'

    ignoreContext = True

    @property
    def ignoreRequest(self):
        return not self.selected_channel
    
    prefix = property(prefix)
    
    def __init__(self, context, request, parentForm):
        self.context = context
        self.request = request
        self.parentForm = self.__parent__ = parentForm
        self.heading = 'Optional sections for %s'%context.Title()

    # TCM: we could maybe pass the portlet assignment object as
    #      context instead of the channel. And then pass
    #      channel only for use in fields()
    #      This would require a new adapter:
    # TypeError: ('Could not adapt', <Assignment at /portal/++contextportlets++plone.leftcolumn/header>, <InterfaceClass collective.dancing.collector.Schema>)

    @z3c.form.button.handler(z3c.form.form.EditForm.buttons['apply'])
    def handleApply(self, action):
        if self.selected_channel:
            data, errors = self.widgets.extract()
            if errors:
                self.status = self.formErrorsMessage
                return
            assignment = self.parentForm.context
            changed = False
            for field, value in data.items():
                if hasattr(assignment, field) and getattr(assignment, field) == value:
                    continue
                setattr(assignment, field, value)
                changed = True
                
            if changed:
                event.notify(
                    lifecycleevent.ObjectModifiedEvent(assignment))
                self.status = self.successMessage
            else:
                self.status = self.noChangesMessage
    
    @property
    def fields(self):
        if self.selected_channel: 
            fields = []
            for name in self.context.collector.schema.names():
                field = self.context.collector.schema.get(name)
                assignment_value = getattr(self.parentForm.context, name)
                field.default = assignment_value
                fields.append((name,field))
            return z3c.form.field.Fields(interface.interface.InterfaceClass(
                'Schema', bases=(ICollectorSchema,),
                attrs=dict(fields)))
        return z3c.form.field.Fields(self.context.collector.schema)

    
    @property
    def label(self):
        return _(u"${channel} options", mapping={'channel':self.channel.Title()})

    @property
    def selected_channel(self):
        return self.context == self.parentForm.context.channel
    
class ChannelSubscribePortletEditForm(z3c.form.form.EditForm):
    """
    """

    template = viewpagetemplatefile.ViewPageTemplateFile('../browser/form-with-subforms.pt')
    fields = z3c.form.field.Fields(IChannelSubscribePortlet)

    css_class = 'editForm portletEditForm'
    heading = _(u"Edit Channel Subscribe Portlet")

    def update(self):
        super(ChannelSubscribePortletEditForm, self).update()
        self.subforms = []
        for channel in self.context.all_channels:
            if channel.collector is not None:
                option_form = EditCollectorOptionsForm(channel,
                                                       self.request,
                                                       self)
                option_form.update()
                self.subforms.append(option_form)
        

class ChannelSubscribePortletEditView(BrowserView):
    __call__ = ViewPageTemplateFile('z3c.plone.portlet.pt')

    label = _(u"Edit Channel Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter channel.")

    def referer(self):
        return self.request.get('referer', '')

    # eventually replace this with a referer and redirect like regular
    # plone portlets. NB: this would require combining the status messages.
    def back_link(self):
        url = self.request.form.get('referer')
        if not url:
            addview = aq_parent(aq_inner(self.context))
            context = aq_parent(aq_inner(addview))
            url = str(component.getMultiAdapter((context, self.request),
                        name=u"absolute_url")) + '/@@manage-portlets'
        return dict(url=url,
                    label=_(u"Back to portlets"))

    def contents(self):
        collective.singing.z2.switch_on(self)
        return ChannelSubscribePortletEditForm(self.context, self.request)()
     
    
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

