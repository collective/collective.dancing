# -*- coding: utf-8 -*-
import datetime
import urllib

from zope import interface
from zope import schema
from zope.schema.vocabulary import SimpleVocabulary
import zope.schema.vocabulary

try:
    from zope.app.pagetemplate import viewpagetemplatefile
except:
    from zope.browserpage import viewpagetemplatefile
try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

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
from collective.dancing import logger
from collective.dancing import MessageFactory as _
from Products.statusmessages.interfaces import IStatusMessage

from plone.uuid.interfaces import IUUID

from collective.singing.channel import channel_lookup

class UIDResolver(object):
    def __init__(self, uid):
        self.uid = uid

    def __call__(self):
        rc = getToolByName(getSite(), 'reference_catalog')
        return FullFormatWrapper(rc.lookupObject(self.uid))


def _assemble_messages(channel_paths, newsletter_uid, newsletter_path,
                       include_collector_items, override_vars=None):
    if override_vars is None:
        override_vars = {}
    queued = 0
    site = getSite()
    request = site.REQUEST
    uid_catalog = getToolByName(site, 'uid_catalog', None)
    newsletter_item = uid_catalog(UID=newsletter_uid)
    if not newsletter_item:
        message = "There was a problem in dispatching newsletters. %s was not found and this queue will be deleted." % newsletter_path
        logger.warning(message)
        IStatusMessage(site.REQUEST).add(message, "warning")
        return _(u"0 messages queued for delivery. Item '${newsletter_path}' not found.",
             mapping=dict(newsletter_path=newsletter_path))
        # raise KeyError('Newsletter not found')
    context = newsletter_item[0].getObject()
    for path in channel_paths:
        channel = site.restrictedTraverse(path)
        assembler = collective.singing.interfaces.IMessageAssemble(channel)
        queued += assembler(
            request, (FullFormatWrapper(context),), include_collector_items, override_vars)
        if channel.scheduler is not None and include_collector_items:
            channel.scheduler.triggered_last = datetime.datetime.now()
    return _(u"${queued} message(s) queued for delivery.",
             mapping=dict(queued=queued))


def ChannelAndCollectorVocab(context):
    terms = []
    for channel in channel_lookup(only_sendable=True):
        # use path so we can store the value savely if needed
        path = '/'.join(channel.getPhysicalPath())
        terms.append(zope.schema.vocabulary.SimpleTerm(
            value=(path, None),
            token=channel.name,
            title=channel.title))
        if channel.collector is not None:
            for collector in channel.collector.get_optional_collectors():
                # the value needs to be collector.title as that is what is stored in the subscription
                terms.append(zope.schema.vocabulary.SimpleTerm(
                    value=(path, collector.title),
                    token=channel.name + "/" + collector.title,
                    title=channel.title + " - " + collector.title
                    ))

    return SimpleVocabulary(terms)


class SendForm(form.Form):
    label = _(u'Send')
    fields = field.Fields(ISendAndPreviewForm).select(
      'channel_and_collector', 'include_collector_items', 'datetime')
    prefix = 'send.'
    ignoreContext = True # The context doesn't provide the data
    template = viewpagetemplatefile.ViewPageTemplateFile('subform-formtab.pt')



    @button.buttonAndHandler(_('Send'), name='send')
    def handle_send(self, action):
        context = self.context.context
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        path = data["channel_and_collector"][0]
        channel_paths = [path]
        newsletter_path = "/".join(context.getPhysicalPath())
        newsletter_uid = IUUID(context)
        include_collector_items = data['include_collector_items']
        override_vars = self.get_override_vars()

        job = collective.singing.async.Job(_assemble_messages,
                                            channel_paths,
                                            newsletter_uid,
                                            newsletter_path,
                                            include_collector_items,
                                            override_vars)
        site = getSite()
        channel = site.unrestrictedTraverse(path)
        title = _(u"Send '${context}' through ${channel}.",
                  mapping=dict(
            context=context.Title().decode(context.plone_utils.getSiteEncoding()),
            channel=u'"%s"' % channel.title))
        job.title = title
        utils.get_queue().pending.append(job)

        self.status = _(u"Messages queued for delivery.")

    @button.buttonAndHandler(_('Schedule distribution'), name='schedule',
                             condition=lambda form:form._have_timed_scheduler())
    def handle_schedule(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        path, section = data["channel_and_collector"]
        site = getSite()
        channel = site.unrestrictedTraverse(path)

        if not isinstance(channel.scheduler,
                          collective.singing.scheduler.TimedScheduler):
            self.status = _("${name} does not support scheduling.",
                            mapping=dict(name=channel.title))
            return
        if not data.get('datetime'):
            self.status = _("Please fill in a date.")
            return

        # XXX: We want to get the UIDResolver through an adapter
        # in the future
        channel.scheduler.items.append((
            data['datetime'], UIDResolver(self.context.context.UID()),
            self.get_override_vars()))

        self.status = _("Successfully scheduled distribution.")

    def _have_timed_scheduler(self):
        for channel in collective.singing.channel.channel_lookup():
            if isinstance(channel.scheduler,
                          collective.singing.scheduler.TimedScheduler):
                return True
        return False

    def get_override_vars(self):
        override_vars = {}
        data, errors = self.extractData()
        if errors:
            return

        for field_name in self.fields.omit('channel', 'address', 'datetime',
                                           'include_collector_items', 'channel_and_collector'):
            if data[field_name] is not None:
                override_vars[field_name] = data[field_name]

        channel_path, section_title = data["channel_and_collector"]
        if section_title is not None:
            site = getSite()
            channel = site.unrestrictedTraverse(channel_path)
            for section in channel.collector.get_optional_collectors():
                if section.title == section_title:
                    override_vars["subscriptions_for_collector"] = section
                    break

        return override_vars


class PreviewForm(form.Form):
    label = _(u'Preview')
    fields = field.Fields(ISendAndPreviewForm).select(
        'channel', 'include_collector_items', 'address')
    prefix = 'preview.'
    ignoreContext = True # The context doesn't provide the data
    template = viewpagetemplatefile.ViewPageTemplateFile('subform-formtab.pt')

    @button.buttonAndHandler(_('Show preview'), name='show_preview')
    def handle_show_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        channel = data['channel']
        name = channel.name
        include_collector_items = data['include_collector_items']

        params = {'name': name,
                  'include_collector_items': int(bool(include_collector_items)),
                  'override_vars': self.get_override_vars()}

        self.request.response.redirect(
            self.context.context.absolute_url() + \
            '/preview-newsletter.html?%s' % urllib.urlencode(params))

    @button.buttonAndHandler(_('Send preview'), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return
        channel = data['channel']
        include_collector_items = data['include_collector_items']
        address = data['address']
        if not address:
            self.status = _(u"The address to send the preview to is missing.")
            return

        queued = 0
        assembler = collective.singing.interfaces.IMessageAssemble(channel)
        assembler.update_cue = False
        subs = channel.subscriptions.query(key=address)

        for sub in subs:
            msg = assembler.render_message(
                self.request,
                sub,
                (FullFormatWrapper(self.context.context),),
                include_collector_items,
                self.get_override_vars())
            if msg is not None:
                queued += 1

        self.status = _(
            u"${num} message(s) queued.", mapping=dict(num=queued))

    def get_override_vars(self):
        override_vars = {}
        data, errors = self.extractData()
        if errors:
            return

        for field_name in self.fields.omit('channel', 'address', 'datetime',
                                           'include_collector_items'):
            if data[field_name] is not None:
                override_vars[field_name] = data[field_name]

        return override_vars


class SendAsNewsletterForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('send-newsletter.pt')
    factories = [SendForm, PreviewForm]

    def update(self):
        super(SendAsNewsletterForm, self).update()

        self.subforms = [f(self, self.request) for f in self.factories]
        for form in self.subforms:
            form.update()

            # XXX: We should find a more beautiful solution here!
            if form.status:
                IStatusMessage(self.request).addStatusMessage(form.status)

    def timed_channels(self):
        channels = []
        for channel in collective.singing.channel.channel_lookup():
            if isinstance(channel.scheduler,
                          collective.singing.scheduler.TimedScheduler):
                channels.append(channel.name)
        return channels


class SendAsNewsletterView(plone.z3cform.layout.FormWrapper):

    form = SendAsNewsletterForm
    request_layer = collective.singing.interfaces.IFormLayer

    def label(self):
        site_encoding = self.context.plone_utils.getSiteEncoding()
        return _(u'Send ${item} as newsletter',
                 mapping=dict(item=self.context.Title().decode(site_encoding)))


# Examples of customized forms, used in testing and docs:

class ISendAndPreviewFormWithCustomSubject(ISendAndPreviewForm):
    subject = schema.TextLine(
        title=_(u"Custom Subject"),
        description=_(u"Enter a custom subject line for your newsletter here. "
                      "Leave blank to use the default subject for the chosen "
                      "content and mailing-list."),
        required=False)


class SendFormWithCustomSubject(SendForm):
    fields = field.Fields(ISendAndPreviewFormWithCustomSubject).select(
        'channel', 'subject', 'include_collector_items', 'datetime')


class PreviewFormWithCustomSubject(PreviewForm):
    fields = field.Fields(ISendAndPreviewFormWithCustomSubject).select(
        'channel', 'subject', 'include_collector_items', 'address')


class SendAsNewsletterFormWithCustomSubject(SendAsNewsletterForm):
    factories = [SendFormWithCustomSubject, PreviewFormWithCustomSubject]


class SendAsNewsletterViewWithCustomSubject(SendAsNewsletterView):
    form = SendAsNewsletterFormWithCustomSubject
