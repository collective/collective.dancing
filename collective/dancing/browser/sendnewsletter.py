import datetime

from zope import interface
from zope import schema

from zope.app.pagetemplate import viewpagetemplatefile
from zope.app.component.hooks import getSite

import z3c.form.interfaces
from z3c.form import form
from z3c.form import subform
from z3c.form import field
from z3c.form import button
from z3c.form import validator

from Products.CMFCore.utils import getToolByName
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.z3cform import z2
import collective.singing.channel
import collective.singing.interfaces

from collective.dancing.composer import FullFormatWrapper
from collective.dancing.browser.interfaces import ISendAndPreviewForm
from collective.dancing import MessageFactory as _

class UIDResolver(object):
    def __init__(self, uid):
        self.uid = uid

    def __call__(self):
        rc = getToolByName(getSite(), 'reference_catalog')
        return rc.lookupObject(self.uid)

class SendAsNewsletterForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    
    ignoreContext = True

    @property
    def fields(self):
        fields = field.Fields(ISendAndPreviewForm)
        if not self._have_timed_scheduler():
            fields['datetime'].mode = z3c.form.interfaces.HIDDEN_MODE
        return fields

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
            assembler = collective.singing.interfaces.IMessageAssemble(channel)
            queued += assembler(
                self.request,
                (FullFormatWrapper(self.context),),                
                include_collector_items)
            if channel.scheduler is not None and include_collector_items:
                channel.scheduler.triggered_last = datetime.datetime.now()

        self.status = _(u"${num} messages queued.", mapping=dict(num=queued))

    @button.buttonAndHandler(_('Show preview'), name='show_preview')
    def handle_show_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        channels = data['channels']
        if len(channels) != 1:
            self.status = _(u"Please select precisely one channel for preview.")
            return

        name = tuple(channels)[0].name
        include_collector_items = data['include_collector_items']
        
        self.request.response.redirect(
            self.context.absolute_url()+\
            '/preview-newsletter.html?name=%s&include_collector_items=%d' % \
            (name, int(bool(include_collector_items))))

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
            assembler = collective.singing.interfaces.IMessageAssemble(channel)
            subs = channel.subscriptions.query(key=address)
            if len(subs) == 0:
                self.status = _(
                    u"${address} is not subscribed to ${channel}.",
                    mapping=dict(address=address, channel=channel.title))
                continue

            for sub in subs:
                assembler.render_message(
                    self.request,
                    sub,
                    (FullFormatWrapper(self.context),),                
                    include_collector_items)
                queued += 1
        if queued:
            self.status = _(
                u"${num} messages queued.", mapping=dict(num=queued))

    def _have_timed_scheduler(self):
        for channel in collective.singing.channel.channel_lookup():
            if isinstance(channel.scheduler,
                          collective.singing.scheduler.TimedScheduler):
                return True
        return False

    @button.buttonAndHandler(_('Schedule distribution'), name='schedule',
                             condition=lambda form:form._have_timed_scheduler())
    def handle_schedule(self, action):
        data, errors = self.extractData()
        channels = data.get('channels', ())
        for channel in channels:
            if not isinstance(channel.scheduler,
                              collective.singing.scheduler.TimedScheduler):
                self.status = _("${name} does not support scheduling.",
                                mapping=dict(name=channel.title))
                return
        if not data.get('datetime'):
            self.status = _("Please fill in a date.")
            return

        for channel in channels:
            # XXX: We want to get the UIDResolver through an adapter
            # in the future
            channel.scheduler.items.append((
                data['datetime'], UIDResolver(self.context.UID())))

        self.status = _("Successfully scheduled distribution.")

class SendAsNewsletterView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        site_encoding = self.context.plone_utils.getSiteEncoding()
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.title.decode(site_encoding)))

    def contents(self):
        z2.switch_on(self,
                     request_layer=collective.singing.interfaces.IFormLayer)
        return SendAsNewsletterForm(self.context, self.request)()
