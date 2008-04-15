import datetime

from zope import schema
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import form
from z3c.form import subform
from z3c.form import field
from z3c.form import button
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import collective.singing.z2
import collective.singing.scheduler

from collective.dancing import MessageFactory as _
from collective.dancing.composer import FullFormatWrapper

class SendAsNewsletterForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    
    ignoreContext = True

    fields = field.Fields(
        schema.Set(
            __name__='channels',
            title=_(u"The channel to send this through"),
            value_type=schema.Choice(
                vocabulary='collective.singing.vocabularies.ChannelVocabulary')
            ),
        schema.Bool(
            __name__='include_collector_items',
            title=_(u"Include collector items"),
            default=True,
            ),
        schema.TextLine(
            __name__='address',
            title=_(u"Address to send the preview to"),
            description=_(
                u"This is only required if you click 'Send preview' below"),
            required=False,
            ),
        )

    @button.buttonAndHandler(_('Send'), name='send')
    def handle_send(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channels = data['channels']
        include_collector_items = data['include_collector_items']

        queued = 0
        for channel in channels:
            queued += collective.singing.scheduler.assemble_messages(
                channel,
                self.request,
                (FullFormatWrapper(self.context),),                
                include_collector_items)
            if channel.scheduler is not None and include_collector_items:
                channel.scheduler.triggered_last = datetime.datetime.now()

        self.status = _(u"${num} messages queued.", mapping=dict(num=queued))

    @button.buttonAndHandler(_('Show preview'), name='show_preview')
    def handle_show_preview(self, action):
        self.request.response.redirect(self.context.absolute_url()+\
                                       '/preview-newsletter.html')

    @button.buttonAndHandler(_('Send preview'), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channels = data['channels']
        include_collector_items = data['include_collector_items']
        address = data['address']

        queued = 0
        for channel in channels:
            subs = channel.subscriptions.query(key=address)
            if len(subs) == 0:
                self.status = _(
                    u"${address} is not subscribed to ${channel}.",
                    mapping=dict(address=address, channel=channel.title))
                continue

            for sub in subs:
                collective.singing.scheduler.render_message(
                    channel,
                    self.request,
                    sub,
                    (FullFormatWrapper(self.context),),                
                    include_collector_items)
                queued += 1
        if queued:
            self.status = _(
                u"${num} messages queued.", mapping=dict(num=queued))

class SendAsNewsletterView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.title))

    def contents(self):
        collective.singing.z2.switch_on(self)
        return SendAsNewsletterForm(self.context, self.request)()
