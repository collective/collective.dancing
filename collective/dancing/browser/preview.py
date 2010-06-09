import datetime
from zope import interface
from zope import component
from zope import schema

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.statusmessages.interfaces import IStatusMessage
from zope.app.publisher.browser import getDefaultViewName

from collective.dancing.composer import FullFormatWrapper
from collective.singing.channel import lookup
from collective.singing.interfaces import ISubscription
from collective.singing.interfaces import IChannel
from collective.singing.interfaces import IMessageAssemble

from collective.dancing import MessageFactory as _

import transaction

class PreviewSubscription(object):
    interface.implements(ISubscription)

    secret = u""
    format = 'html'

    def __init__(self, channel):
        self.channel = channel

        self.collector_data = {}
        self.metadata = dict(format=self.format,
                             date=datetime.datetime.now() - \
                             datetime.timedelta(days=7),)

        composer = self.channel.composers[self.format]

        # set default composer data
        self.composer_data = dict(
            (name, field.default) \
            for name, field in schema.getFields(composer.schema).items())

class PreviewNewsletterView(BrowserView):
    template = ViewPageTemplateFile("preview.pt")

    def __call__(self, name=None, include_collector_items=False, override_vars=None):

        if override_vars is None:
            override_vars = '{}'

        try:
            include_collector_items = int(include_collector_items)
        except ValueError:
            include_collector_items = False

        if IChannel.providedBy(self.context):
            channel = self.context
            items = ()
        else:
            assert name is not None
            channel = lookup(name)
            items = (FullFormatWrapper(self.context),)

        sub = PreviewSubscription(channel)

        # We don't want to commit a transaction just for the preview;
        # this would happen if we were to simply add and remove from
        # the queue.
        sp = transaction.savepoint()

        message = IMessageAssemble(channel).render_message(
            self.request,
            sub,
            items,
            bool(include_collector_items),
            eval(override_vars))

        if message is None:
            IStatusMessage(self.request).addStatusMessage(
                _(u"No items found."))

            return self.request.response.redirect(self.context.absolute_url())

        # pull message out of hat
        channel.queue[message.status].pull(-1)

        # rollback savepoint
        sp.rollback()

        # walk message, decoding HTML payload
        for part in message.payload.walk():
            if part.get_content_type() == 'text/html':
                html = part.get_payload(decode=True)
                break
        else:
            raise ValueError("Message does not contain a 'text/html' part.")

        return self.template(content=html, title=channel.title)
