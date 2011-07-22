import persistent.dict
from Acquisition import aq_parent, aq_inner
from zope import component
from zope import interface
from zope import schema
from plone.portlets.interfaces import IPortletDataProvider
from plone.app.portlets.portlets import base
from zope.app.pagetemplate import viewpagetemplatefile

from Products.CMFCore.utils import getToolByName
from urllib import urlencode
from Products.Five import BrowserView
import z3c.form

from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from collective.singing.channel import channel_lookup
from collective.dancing import MessageFactory as _
from collective.dancing.browser.subscribe import SubscriptionAddForm
from collective.singing.interfaces import ICollectorSchema
from collective.dancing.utils import switch_on


test_vocab = schema.vocabulary.SimpleVocabulary.fromValues(range(5))

class IChannelSubscribePortlet(IPortletDataProvider):
    """A portlet which renders the results of a collection object.
    """

    header = schema.TextLine(title=_(u"Portlet header"),
                             description=_(u"Title of the rendered portlet"),
                             required=True)
    channel = schema.Choice(title=_(u"The mailing-list to enable subscriptions to."),
                            description=_(u"Find the mailing-list you want to enable direct subscription to"),
                            required=False,
                            vocabulary='collective.singing.vocabularies.ChannelVocabulary'
                            )
    description = schema.TextLine(title=_(u"Portlet description"),
                           description=_(u"Description of the rendered portlet"),
                           required=True)
    subscribe_directly = schema.Bool(title=_(u"Subscribe directly from portlet"),
                            description=_(u"Click here to select collector options to be automatically enabled, when subscribing from this portlet."),
                            required=True,
                            default=True)
    footer_text = schema.TextLine(title=_(u"Footer text"),
                             description=_(u"Text in footer - if omitted the mailing-list title is used"),
                             required=False)

    show_footer = schema.Bool(title=_(u"Show footer"),
                            description=_(u"Click here to show the portlet footer."),
                            required=True,
                            default=True)

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
    subscribe_directly = True

    def __init__(self,
                 header=u"",
                 description=u"",
                 channel=None,
                 subscribe_directly=True,
                 footer_text="",
                 show_footer=True):
        self.header = header
        self.description = description
        self._channel = channel
        self.subscribe_directly = subscribe_directly
        self.footer_text = footer_text
        self.show_footer = show_footer

    @apply
    def channel():
        def get(self):
            # BBB: Versions prior to r67243 used to have an attribute
            # called 'channel'; then it's become a property
            channel = self.__dict__.get('channel')
            if channel is None:
                channel = self._channel
            if channel is not None:
                for c in self.all_channels:
                    if c.name == channel.name:
                        return c
            return None
        def set(self, value):
            self._channel = value
        return property(get, set)


    @property
    def title(self):
        """This property is used to give the title of the portlet in the
        "manage portlets" screen. Here, we use the title that the user gave.
        """
        return self.header

    @property
    def all_channels(self):
        return channel_lookup(only_subscribeable=True)

class ValuesMixin(object):
    """Mix-in class that allows convenient access to data stored on
    the assignment."""

    channel_id = None
    assignment = None

    @apply
    def stored_values():
        def get(self):
            d = getattr(self.assignment, '_stored_values',
                        persistent.dict.PersistentDict())
            return d.setdefault(
                self.channel_id, persistent.dict.PersistentDict())
        def set(self, value):
            d = getattr(self.assignment, '_stored_values',
                        persistent.dict.PersistentDict())
            d[self.channel_id] = value
            self.assignment._stored_values = d
        return property(get, set)

class PortletSubscriptionAddForm(ValuesMixin, SubscriptionAddForm):
    """ """
    template = viewpagetemplatefile.ViewPageTemplateFile('htmlstatusform.pt')

    assignment = None

    @property
    def status_already_subscribed(self):
        link_start = '<a href="%s/sendsecret.html">' % (
            self.newslettertool.absolute_url())
        link_end = '</a>'
        # The link_start plus link_end construction is not very
        # pretty, but it is needed to avoid syntax errors in the
        # generated po files.
        return _(
            u'You are already subscribed to this newsletter. Click here to '
            '${link_start}edit your subscriptions${link_end}.',
            mapping={'link_start': link_start,
                     'link_end': link_end})

    @property
    def newslettertool(self):
        return getToolByName(self.context, 'portal_newsletters')

    def update(self):
        super(PortletSubscriptionAddForm, self).update()
        self.channel_id = self.context.id

        if self.context.collector is not None:
            stored_values = self.stored_values
            collector_schema = self.context.collector.schema

            for name in collector_schema.names():
                field = collector_schema.get(name)
                widget = self.widgets['collector.' + name]
                value = stored_value = stored_values.get(name)
#                 if stored_value is not None:
#                     subfield = field
#                     vocabulary = None
#                     while (not hasattr(subfield, 'vocabulary')) and \
#                               (hasattr(subfield, 'value_type')):
#                         subfield = subfield.value_type
#                     if hasattr(subfield, 'vocabulary'):
#                         if
#                         value = set([v for v in stored_value
#                                      if v in subfield.vocabulary])
                if value:
                    converter = z3c.form.interfaces.IDataConverter(widget)
                    widget.value = converter.toWidgetValue(stored_value)
#                else:
#                    widget.value = value
                widget.update()

    @property
    def fields(self):
        fields = z3c.form.field.Fields(
            self.context.composers[self.format].schema,
            prefix='composer.')
        if self.context.collector is not None and self.assignment.subscribe_directly:
            fields += z3c.form.field.Fields(self.context.collector.schema,
                                            prefix='collector.',
                                            mode=z3c.form.interfaces.HIDDEN_MODE)
        return fields

class PortletSubscribeLinkForm(z3c.form.form.Form):
    """ """
    template = viewpagetemplatefile.ViewPageTemplateFile('titlelessform.pt')
    ignoreContext = True
    formErrorsMessage = _('There were some errors.')

    def __init__(self, context, request):
        super(PortletSubscribeLinkForm, self).__init__(context, request)

    @property
    def fields(self):
        return z3c.form.field.Fields(self.context.composers[self.format].schema)

    @z3c.form.button.buttonAndHandler(_('Proceed'), name='preceed')
    def handleAdd(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        params = urlencode(dict([('composer.widgets.%s'%key, value)
                                 for key, value in data.items()]))
        subscribe_url = '%s/subscribe.html?%s' % (self.context.absolute_url(),
                                                  params)
        self.request.response.redirect(subscribe_url)
        return

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

    def setup_form(self):
        switch_on(self)
        if self.channel is not None:
            if self.data.subscribe_directly:
                self.form = PortletSubscriptionAddForm(self.channel, self.request)
                self.form.assignment = self.data
            else:
                self.form = PortletSubscribeLinkForm(self.channel, self.request)
            self.form.format = 'html'
            self.form.update()

    def render(self):
        self.setup_form()
        return self._template()

    @property
    def available(self):
        return bool(self.data.channel)

    @property
    def channel(self):
        return self.data.channel
        channels = self.data.all_channels
        if channels and self.data.channel:
            for channel in channels:
                if channel.name == self.data.channel.name:
                    return channel
        return None

    def channel_link(self):

        link = {'url':'%s/subscribe.html'%self.channel.absolute_url(),
                'title':self.getFooterText()}
        return link


    def getFooterText(self):
        if bool(self.data.footer_text):
            return self.data.footer_text
        return self.channel.Title()


def prefix(self):
    return str(self.__class__.__name__ + '-'.join(self.context.getPhysicalPath()))


class EditCollectorOptionsForm(ValuesMixin, z3c.form.subform.EditSubForm):
    """Edit a single collectors options."""
    template = viewpagetemplatefile.ViewPageTemplateFile(
        '../subform.pt')

    css_class = 'subForm subForm-level-1'
    ignoreContext = True

    @property
    def heading(self):
        return _(u"${channel} options", mapping={'channel':self.context.Title()})

    prefix = property(prefix)

    @property
    def fields(self):
        return z3c.form.field.Fields(self.context.collector.schema)


    @property
    def channel_id(self):
        return self.context.id

    @property
    def assignment(self):
        return self.parentForm.context

    @z3c.form.button.handler(z3c.form.form.EditForm.buttons['apply'])
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        stored_values = self.stored_values
        changed = False

        for name, widget_value in data.items():
            if stored_values.get(name) == widget_value:
                continue
            else:
                stored_values[name] = widget_value
            changed = True

        if changed:
            self.stored_values = stored_values
            self.status = self.successMessage
        else:
            self.status = self.noChangesMessage

    def update(self):
        super(EditCollectorOptionsForm, self).update()

        # We add some logic here to set widget values from stored
        # values if they weren't provided in the request.  Note that
        # we have ``ignoreContext = True``.

        stored_values = self.stored_values
        for name in self.context.collector.schema.names():
            field = self.context.collector.schema.get(name)
            widget = self.widgets[name]
            stored_value = stored_values.get(name)
            widget_value = widget.extract()

            if (widget_value is z3c.form.interfaces.NOVALUE and
                stored_value is not None):

                # discard values that are not in this collectors vocabulary
                # The collector may be changed or entirely different since
                # last save.
                subfield = field
                vocabulary = None
                while (not hasattr(subfield, 'vocabulary')) and \
                          (hasattr(subfield, 'value_type')):
                    subfield = subfield.value_type
                if hasattr(subfield, 'vocabulary'):
                    value = set([v for v in stored_value
                                 if v in subfield.vocabulary])

                if len(value):
                    converter = z3c.form.interfaces.IDataConverter(widget)
                    widget.value = converter.toWidgetValue(value)
                else:
                    widget.value = value
                widget.update()

class ChannelSubscribePortletEditForm(z3c.form.form.EditForm):
    """  """
    template = viewpagetemplatefile.ViewPageTemplateFile('../form-with-subforms.pt')
    fields = z3c.form.field.Fields(IChannelSubscribePortlet)

    css_class = 'editForm portletEditForm'
    heading = _(u"Edit Mailing-list Subscribe Portlet")

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

    label = _(u"Edit Mailing-list Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter.")

    def contents(self):
        switch_on(self)
        return ChannelSubscribePortletEditForm(self.context, self.request)()


class EditCollectorOptionsAddForm(z3c.form.form.Form):
    """Edit a single collectors options.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile(
        '../subform.pt')

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
    template = viewpagetemplatefile.ViewPageTemplateFile('../form-with-subforms.pt')
    fields = z3c.form.field.Fields(IChannelSubscribePortlet)

    css_class = 'addForm portletAddForm'
    heading = _(u"Add Mailing-list Subscribe Portlet")

    subforms = []

    def create(self, data):
        return Assignment(**data)

    def add(self, object):
        self.context.add(object)

    def nextURL(self):
        # XXX: this should be prettier/more stable
        subscribe_directly = self.request.get(
            'form.widgets.subscribe_directly', '') == [u'true']
        if subscribe_directly:
            return '../%s/edit' % (self.context.items()[-1][0])
        else:
            return '../../@@manage-portlets'


class ChannelSubscribePortletAddView(ChannelSubscribePortletView):

    label = _(u"Add Mailing-list Subscribe Portlet")
    description = _(u"This portlet allows a visitor to subscribe to a specific newsletter.")

    def contents(self):
        switch_on(self)
        return ChannelSubscribePortletAddForm(self.context, self.request)()

