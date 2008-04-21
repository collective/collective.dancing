import datetime
from zope import component
from zope import interface
from zope import schema
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from z3c.form import button
from z3c.form import field
from collective.singing import interfaces
from plone.z3cform import z2
from plone.z3cform.crud import crud

from collective.dancing.browser import controlpanel
from collective.dancing import MessageFactory as _

class IQueueStatistics(interface.Interface):
    title = schema.TextLine(title=_(u"Title"))

    messages_sent = schema.Int(
        title=_(u"Total messages sent"),
        description=_(u"Total number of messages sent successsfully"),
        )

    new_messages = schema.Int(
        title=_(u"New messages"),
        description=_(u"Messages waiting to be sent"),
        )
    new_last_modified = schema.Datetime(title=_(u"Last Change"))

    sent_messages = schema.Int(
        title=_(u"Sent messages"),
        description=_(u"Messages successfully sent"),
        )
    sent_last_modified = schema.Datetime(title=_(u"Last Change"))

    error_messages = schema.Int(
        title=_(u"Failed messages"),
        description=_(u"Messages with errors"),
        )
    error_last_modified = schema.Datetime(title=_(u"Last Change"))

    retry_messages = schema.Int(
        title=_(u"Retry messages"),
        description=_(u"Messages with errors in the retry queue"),
        )
    retry_last_modified = schema.Datetime(title=_(u"Last Change"))

class ChannelStatistics(object):
    interface.implements(IQueueStatistics)
    component.adapts(interfaces.IChannel)

    def __init__(self, channel):
        self.channel = channel
        self.title = channel.title

        self.messages_sent = channel.queue.messages_sent
        for status in interfaces.MESSAGE_STATES:
            size, date = self._get_queue_info(channel.queue, status)
            setattr(self, '%s_messages' % status, size)
            setattr(self, '%s_last_modified' % status, date)

    @staticmethod
    def _get_queue_info(queue, status):
        msg_count = len(queue[status])
        if msg_count:
            last_modified = queue[status][-1].status_changed
        else:
            last_modified = None
        return msg_count, last_modified

class EditForm(crud.EditForm):
    @button.buttonAndHandler(_('Flush old messages'), name='flush')
    def handle_flush(self, action):
        self.status = _(u"Please select items to flush.")
        selected = self.selected_items()
        if selected:
            self.status = _(u"Successfully flushed channels.")
            for id, stats in selected:
                stats.channel.queue.flush()

    @button.buttonAndHandler(_('Send messages now'), name='send')
    def handle_send(self, action):
        self.status = _(u"Please select which channel you'd like to send "
                        "queued e-mails of.")
        selected = self.selected_items()
        if selected:
            sent, failed = 0, 0
            for id, stats in selected:
                s, f = stats.channel.queue.dispatch()
                sent += s
                failed += f
            self.status = _(u"${sent} message(s) sent, ${failed} failure(s).",
                            mapping=dict(sent=sent, failed=failed))

class StatsForm(crud.CrudForm):
    """View list of queues and last modification dates for all
    available channels.
    """
    addform_factory = crud.NullForm
    editform_factory = EditForm
    view_schema = IQueueStatistics

    def get_items(self):
        return [(channel.name, ChannelStatistics(channel)) for channel in
                component.getUtility(interfaces.IChannelLookup)()]

    def remove(self, (id, item)):
        for name, stats in self.get_items():
            if name == id:
                stats.channel.queue.flush()
                self.status = _(u"All sent and failed messages deleted")
                return
        else:
            raise KeyError(id)

class StatsView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    label = _(u"Newsletter statistics")
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return StatsForm(None, self.request)()
