from zope import interface
from zope import schema
from zope import component
from zope.app.pagetemplate import viewpagetemplatefile
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from z3c.form import form
from z3c.form import field
from z3c.form import button
from z3c.form import term
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.interfaces import ISequenceWidget

from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

import collective.singing.z2
import collective.singing.scheduler

from collective.dancing import MessageFactory as _
from collective.singing.interfaces import IChannel
from collective.singing.subscribe import SubscriptionQuerySourceBinder

from z3c.formwidget.query.widget import QuerySourceFieldWidget

import datetime
import urllib

class ISendAsNewsletter(interface.Interface):
    channel = schema.Choice(
        title=_(u"Select channel"),
        description=_(u"This item will be send to the subscribers "
                      "of the selected channel."),
        vocabulary='collective.dancing.vocabularies.ChannelVocabulary',
        required=True,
        )

    include_collector_items = schema.Bool(
        title=_(u"Include collector items"),
        default=True,
        )

class SendAsNewsletterForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    
    ignoreContext = True

    fields = field.Fields(ISendAsNewsletter)

    @button.buttonAndHandler(_('Send'), name='send')
    def handle_send(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channel = data['channel']
        include_collector_items = data['include_collector_items']

        queued = collective.singing.scheduler.assemble_messages(
            channel, (self.context,), include_collector_items)

        if channel.scheduler is not None and include_collector_items:
            channel.scheduler.triggered_last = datetime.datetime.now()

        channel.queue.dispatch()

        self.status = _(u"${num} messages queued.", mapping=dict(num=queued))

    @button.buttonAndHandler(_('Preview...'), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        # redirect to preview
        prefix = self.prefix
        parameters = {prefix+'channel': data['channel'].name,
                      prefix+'include_collector_items': data['include_collector_items']}

        self.request.response.redirect(self.context.absolute_url() + \
             '/preview-newsletter.html?%s' % urllib.urlencode(parameters))

class SendAsNewsletterPreviewForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    
    ignoreContext = True

    @property
    def fields(self):
        """Dynamic fields generator.

        This sets up form fields and preps the 'subscription' field
        source with the currently active channel.

        A bit of hack.
        """
        
        channel_names = self.request.form.get(
            self.prefix+'widgets.channel')
        
        if channel_names is not None:
            channel = component.getUtility(IChannel, name=channel_names[0])
        else:
            channel = None

        fields = field.Fields(
            ISendAsNewsletter,
            schema.Choice(
            __name__='subscription',
            title=_(u"Subscriber"),
            description=_(u"Search for a subscriber."),
            source=SubscriptionQuerySourceBinder(channels=(channel,)),
            required=False))

        # set query source widget
        fields['subscription'].widgetFactory = QuerySourceFieldWidget

        return fields
    
    @button.buttonAndHandler(_('Send preview'), name='send')
    def handle_send(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        # TODO
        
class SendAsNewsletterView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.title))

    def contents(self):
        collective.singing.z2.switch_on(self)
        return SendAsNewsletterForm(self.context, self.request)()

class SendAsNewsletterPreviewView(SendAsNewsletterView):
    def label(self):
        return _(u'Preview ${item} as newsletter',
                 mapping=dict(item=self.context.title))
    
    def contents(self):
        collective.singing.z2.switch_on(self)
        return SendAsNewsletterPreviewForm(self.context, self.request)()
