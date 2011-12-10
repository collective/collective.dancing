from zope import component
from zope import interface
from zope import schema
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zope.app.pagetemplate import viewpagetemplatefile

from z3c.form import button

from plone.app.z3cform import layout
from plone.z3cform.crud import crud
from collective.singing import interfaces
from collective.singing.channel import channel_lookup

from collective.dancing.browser import controlpanel
from collective.dancing import utils
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
    jobs_template = viewpagetemplatefile.ViewPageTemplateFile('jobs.pt')

    def render(self):
        # In addition to rendering the usual crud table, we'll add a
        # table with information about jobs at the top:
        html = u''
        if self.pending_jobs() or self.finished_jobs():
            html = self.jobs_template()

        return html + super(EditForm, self).render()

    @button.buttonAndHandler(_('Remove old messages'), name='removeold')
    def handle_clear(self, action):
        self.status = _(u"Please select items to remove.")
        selected = self.selected_items()
        if selected:
            self.status = _(u"Successfully removed old messages from mailing-lists.")
            for id, stats in selected:
                stats.channel.queue.clear()

    @button.buttonAndHandler(_('Clear queued messages'), name='clearnew')
    def handle_clearnew(self, action):
        self.status = _(u"Please select items with new messages to clear.")
        selected = self.selected_items()
        if selected:
            self.status = _(u"Successfully cleared queued messages in mailing-lists.")
            for id, stats in selected:
                stats.channel.queue.clear(queue_names=('new','retry'))

    @button.buttonAndHandler(_('Send queued messages now'), name='send')
    def handle_send(self, action):
        self.status = _(u"Please select which mailing-list's queued e-mails"
                        " you'd like to send.")
        selected = self.selected_items()
        if selected:
            sent, failed = 0, 0
            for id, stats in selected:
                s, f = stats.channel.queue.dispatch()
                sent += s
                failed += f
            self.status = _(u"${sent} message(s) sent, ${failed} failure(s).",
                            mapping=dict(sent=sent, failed=failed))

    @button.buttonAndHandler(_('Process jobs'), name='process_jobs',
                             condition=lambda form: form.pending_jobs())
    def handle_process_jobs(self, action):
        queue = utils.get_queue()
        num = queue.process()
        finished = queue.finished[-num:]
        if len(finished) == 1:
            self.status = finished[0].value
        else:
            self.status = _(u"All pending jobs processed")

    @button.buttonAndHandler(_('Clear finished jobs'), name='clear_jobs',
                             condition=lambda form: form.finished_jobs())
    def handle_clear_jobs(self, action):
        queue = utils.get_queue()
        while queue.finished:
            queue.finished.pop()
        self.status = _("All finished jobs cleared")

    def pending_jobs(self):
        return utils.get_queue().pending

    def finished_jobs(self):
        return utils.get_queue().finished

class StatsForm(crud.CrudForm):
    """View list of queues and last modification dates for all
    available channels.
    """
    addform_factory = crud.NullForm
    editform_factory = EditForm
    view_schema = IQueueStatistics

    def get_items(self):
        return [(channel.name, ChannelStatistics(channel))
                for channel in channel_lookup()]

    def remove(self, (id, item)):
        for name, stats in self.get_items():
            if name == id:
                stats.channel.queue.clear()
                self.status = _(u"All sent and failed messages deleted")
                return
        else:
            raise KeyError(id)

StatsView = layout.wrap_form(
    StatsForm,
    index=ViewPageTemplateFile('controlpanel.pt'),
    label = _(u"label_statistics_administration",
              default=u"Statistics"),
    back_link = controlpanel.back_to_controlpanel)
