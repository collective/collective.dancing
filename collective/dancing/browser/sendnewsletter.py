import datetime

from zope import schema
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import form
from z3c.form import field
from z3c.form import button
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import collective.singing.z2
import collective.singing.scheduler

from collective.dancing import MessageFactory as _
from collective.dancing.composer import FullFormat

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
                (FullFormat(self.context),),
                include_collector_items)
            if channel.scheduler is not None and include_collector_items:
                channel.scheduler.triggered_last = datetime.datetime.now()
            channel.queue.dispatch()

        self.status = _(u"${num} messages queued.", mapping=dict(num=queued))

class SendAsNewsletterView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.title))

    def contents(self):
        collective.singing.z2.switch_on(self)
        return SendAsNewsletterForm(self.context, self.request)()
