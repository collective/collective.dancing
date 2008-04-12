import datetime
import urllib

from zope import interface
from zope import schema
from zope import component
from zope.app.pagetemplate import viewpagetemplatefile
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary
from z3c.form import form
from z3c.form import field
from z3c.form import button
import z3c.form.interfaces
from z3c.form.browser.checkbox import CheckBoxFieldWidget
from z3c.form.interfaces import ISequenceWidget
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.formwidget.query.widget import QuerySourceFieldWidget

import collective.singing.z2
import collective.singing.scheduler
import collective.singing.interfaces
from collective.singing.vocabularies import SubscriptionQuerySourceBinder

from collective.dancing import MessageFactory as _

class ISendAsNewsletter(interface.Interface):
    channel = schema.Choice(
        title=_(u"Select channel"),
        description=_(u"This item will be send to the subscribers "
                      "of the selected channel."),
        vocabulary='collective.singing.vocabularies.ChannelVocabulary',
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

        self.status = _(u"${num} messages queued.", mapping=dict(num=queued))

    @button.buttonAndHandler(_('Preview...'), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        # redirect to preview
        prefix = self.prefix + self.widgets.prefix
        parameters = {prefix + 'channel:list': data['channel'].name}
        if data['include_collector_items']:
            parameters[prefix + 'include_collector_items'] = 'true'
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
        
        channel_name = self.request.form.get('form.channel')
        if channel_name is not None:
            channels = component.getUtility(
                collective.singing.interfaces.IChannelLookup)()
            channel = [c for c in channels if c.name == channel_name]
            source = SubscriptionQuerySourceBinder(channels=(channel,))
        else:
            source = SubscriptionQuerySourceBinder()

        fields = z3c.form.field.Fields(
            ISendAsNewsletter,
            schema.Choice(__name__='subscription',
                          title=_(u"Subscriber"),
                          description=_(u"Search for a subscriber."),
                          source=source,
                          required=False))

        fields['subscription'].widgetFactory = QuerySourceFieldWidget

        for f in fields['channel'], fields['include_collector_items']:
            f.mode = z3c.form.interfaces.HIDDEN_MODE
        return fields
    
    @button.buttonAndHandler(_('Send preview'), name='send')
    def handle_send(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        message = collective.singing.scheduler.render_message(
            data['channel'],
            data['subscription'].value, #XXX: Why are we getting a term here?
            (self.context,),
            data['include_collector_items'])

        if message is not None:
            self.status = _(u"Message queued.")

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
