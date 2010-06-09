import datetime
import urllib

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
import plone.z3cform.layout
import collective.singing.async
import collective.singing.channel
import collective.singing.interfaces

from collective.dancing.composer import FullFormatWrapper
from collective.dancing.browser.interfaces import ISendAndPreviewForm
from collective.dancing import utils
from collective.dancing import MessageFactory as _

class UIDResolver(object):
    def __init__(self, uid):
        self.uid = uid

    def __call__(self):
        rc = getToolByName(getSite(), 'reference_catalog')
        return FullFormatWrapper(rc.lookupObject(self.uid))

def _assemble_messages(channel_paths, context_path,
                       include_collector_items, override_vars=None):
    if override_vars is None:
        override_vars = {}
    queued = 0
    site = getSite()
    request = site.REQUEST
    context = site.restrictedTraverse(context_path)
    for path in channel_paths:
        channel = site.restrictedTraverse(path)
        assembler = collective.singing.interfaces.IMessageAssemble(channel)
        queued += assembler(
            request, (FullFormatWrapper(context),), include_collector_items, override_vars)
        if channel.scheduler is not None and include_collector_items:
            channel.scheduler.triggered_last = datetime.datetime.now()
    return "%s message(s) queued for delivery." % queued

class SendAsNewsletterForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    ignoreContext = True

    @property
    def fields(self):
        fields = field.Fields(ISendAndPreviewForm)
        if not self._have_timed_scheduler():
            fields['datetime'].mode = z3c.form.interfaces.HIDDEN_MODE
        return fields

    def get_override_vars(self):
        override_vars = {}
        data, errors = self.extractData()
        if errors:
            return

        for field_name in self.fields.omit('channels', 'address', 'datetime',
                                           'include_collector_items'):
            if data[field_name] is not None:
                override_vars[field_name] = data[field_name]

        return override_vars

    @button.buttonAndHandler(_('Send'), name='send')
    def handle_send(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channels = data['channels']
        channel_paths = ['/'.join(c.getPhysicalPath()) for c in channels]
        context_path = '/'.join(self.context.getPhysicalPath())
        include_collector_items = data['include_collector_items']
        override_vars = self.get_override_vars()

        job = collective.singing.async.Job(
            _assemble_messages,
            channel_paths, context_path, include_collector_items, override_vars)
        title = _(u"Send '${context}' through ${channels}.",
                  mapping=dict(
            context=self.context.Title().decode(self.context.plone_utils.getSiteEncoding()),
            channels=u', '.join([u'"%s"' % c.title for c in channels])))
        job.title = title
        utils.get_queue().pending.append(job)

        self.status = _(u"Messages queued for delivery.")

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

        params = {'name': name,
                  'include_collector_items': int(bool(include_collector_items)),
                  'override_vars': self.get_override_vars()}

        self.request.response.redirect(
            self.context.absolute_url()+\
            '/preview-newsletter.html?%s' % urllib.urlencode(params))

    @button.buttonAndHandler(_('Send preview'), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channels = data['channels']
        include_collector_items = data['include_collector_items']
        address = data['address']
        if not address:
            self.status = _(u"The address to send the preview to is missing.")
            return

        queued = 0
        for channel in channels:
            assembler = collective.singing.interfaces.IMessageAssemble(channel)
            assembler.update_cue = False
            subs = channel.subscriptions.query(key=address)

            for sub in subs:
                msg = assembler.render_message(
                    self.request,
                    sub,
                    (FullFormatWrapper(self.context),),
                    include_collector_items,
                    self.get_override_vars())
                if msg is not None:
                    queued += 1

        self.status = _(
            u"${num} message(s) queued.", mapping=dict(num=queued))

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
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

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
                data['datetime'], UIDResolver(self.context.UID()),
                self.get_override_vars()))

        self.status = _("Successfully scheduled distribution.")

class SendAsNewsletterView(plone.z3cform.layout.FormWrapper):

    form = SendAsNewsletterForm
    request_layer = collective.singing.interfaces.IFormLayer

    def label(self):
        site_encoding = self.context.plone_utils.getSiteEncoding()
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.Title().decode(site_encoding)))




class ISendAndPreviewFormWithCustomSubject(ISendAndPreviewForm):
    subject = schema.TextLine(
        title=_(u"Custom Subject"),
        description=_(u"Enter a custom subject line for your newsletter here. "
                      "Leave blank to use the default subject for the chosen "
                      "content and channel."),
        required=False)

class SendAsNewsletterFormWithCustomSubject(SendAsNewsletterForm):
    @property
    def fields(self):
        fields = field.Fields(ISendAndPreviewFormWithCustomSubject)
        if not self._have_timed_scheduler():
            fields['datetime'].mode = z3c.form.interfaces.HIDDEN_MODE
        return fields

class SendAsNewsletterViewWithCustomSubject(SendAsNewsletterView):
    form = SendAsNewsletterFormWithCustomSubject
