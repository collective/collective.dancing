import random
import string
from UserString import UserString

import persistent.dict
from zope import component
from zope import interface
from zope import schema
import zope.app.container.interfaces
import zope.app.component.hooks
import AccessControl
from Acquisition import aq_base
import OFS.event
import OFS.Folder
import OFS.SimpleItem
import Products.CMFPlone.interfaces
import collective.singing.interfaces
import collective.singing.message
import collective.singing.channel
import collective.singing.subscribe
import collective.dancing.collector
import collective.dancing.composer
import collective.dancing.subscribe
import collective.dancing.utils
from collective.dancing import MessageFactory as _

def portal_newsletters():
    """Return mailing-lists created with the newsletter tool."""

    root = component.queryUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    if root is None:
        return []
    root = collective.dancing.utils.fix_request(root, 0)
    if 'portal_newsletters' in root.objectIds():
        channels = root['portal_newsletters']['channels'].objectValues()
        security = AccessControl.getSecurityManager()
        return [c for c in channels if
                security.checkPermission('View', c) and
                collective.singing.interfaces.IChannel.providedBy(c)]
    else:
        return []

interface.directlyProvides(portal_newsletters,
                           collective.singing.interfaces.IChannelLookup)

class Salt(UserString):
    """
      >>> len(Salt())
      50
    """
    interface.implements(collective.singing.interfaces.ISalt)

    def __init__(self, data=''):
        if data:
            UserString.__init__(self, data)
            return
        salt = ''.join([
            random.choice(string.ascii_letters + string.digits)
            for i in range(50)])
        UserString.__init__(self, salt)

class INewslettersSettings(interface.Interface):
    use_single_form_subscriptions_page = schema.Bool(
        title=_(u"Use single form subscriptions page"),
        description=_(u"Use single form subscriptions page when possible."),
        default=False,
        required=False)

class IPortalNewsletters(INewslettersSettings):
    pass

class PortalNewsletters(OFS.Folder.Folder):
    interface.implements(IPortalNewsletters)

    use_single_form_subscriptions_page = False

    def Title(self):
        return _(u"Newsletters")

@component.adapter(IPortalNewsletters,
                   zope.app.container.interfaces.IObjectAddedEvent)
def tool_added(tool, event):
    # Add children
    factories = dict(channels=ChannelContainer,
                     collectors=collective.dancing.collector.CollectorContainer)
    existing = tool.objectIds()
    for name, factory in factories.items():
        if name not in existing:
            tool[name] = factory(name)

    # Create and register salt
    salt = getattr(aq_base(tool), 'salt', Salt())
    tool.salt = salt
    sm = zope.component.getSiteManager(tool)
    sm.registerUtility(salt, collective.singing.interfaces.ISalt)

class IChannelContainer(interface.Interface):
    pass

class ChannelContainer(OFS.Folder.Folder):
    interface.implements(IChannelContainer)
    """
      >>> container = ChannelContainer('xs')
      >>> container['your-channel'] = Channel('wq')
      >>> container.objectIds()
      ['your-channel']
    """
    def Title(self):
        return u"Mailing-lists"

@component.adapter(IChannelContainer,
                   zope.app.container.interfaces.IObjectAddedEvent)
def channels_added(container, event):
    if 'default-channel' not in container.objectIds():
        default_channel = Channel('default-channel', title=_(u"Newsletter"))
        container['default-channel'] = default_channel

class Channel(OFS.SimpleItem.SimpleItem):
    """
      >>> channel = Channel('xs')
      >>> from zope.interface.verify import verifyObject
      >>> verifyObject(collective.singing.interfaces.IChannel, channel)
      True
      >>> channel.name
      'xs'
    """
    interface.implements(collective.singing.interfaces.IChannel)

    type_name = _("Standard Channel")

    subscribeable = True

    sendable = True

    keep_sent_messages = collective.singing.interfaces.IChannel[
        'keep_sent_messages'].default

    def __init__(self, name, title=None, composers=None,
                 collector=None, scheduler=None, description=u"", subscribeable=False):
        self.name = name
        if title is None:
            title = name
        self.title = title
        self.description = description
        self.subscribeable = subscribeable
        self.subscriptions = collective.dancing.subscribe.Subscriptions()
        if composers is None:
            composers = persistent.dict.PersistentDict()
            composers['html'] = collective.dancing.composer.HTMLComposer()
        self.composers = composers
        self.collector = collector
        self.scheduler = scheduler
        self.queue = collective.singing.message.MessageQueues()
        super(Channel, self).__init__()

    @property
    def id(self):
        return self.name

    def Title(self):
        return self.title

@component.adapter(Channel,
                   zope.app.container.interfaces.IObjectAddedEvent)
def channel_added(channel, event):
    # We'll take extra care that when we're imported through the ZMI,
    # we update things to keep everything up to date:
    subscriptions = collective.singing.subscribe.subscriptions_data(channel)
    subscriptions._catalog.clear()

    for subscription in subscriptions.values():
        # Let's make sure that ``subscription.channel`` refers to the
        # channel:
        if aq_base(subscription.channel) is not aq_base(channel):
            subscription.channel = channel

        # The secret may have changed:
        composer = channel.composers[subscription.metadata['format']]
        secret = composer.secret(subscription.composer_data)
        if subscription.secret != secret:
            subscription.secret = secret

        # This will finally catalog the subscription:
        collective.singing.subscribe.subscription_added(subscription, None)

@component.adapter(collective.singing.interfaces.ICollector,
                   zope.app.container.interfaces.IObjectRemovedEvent)
def collector_removed(collector, event):
    for channel in collective.singing.channel.channel_lookup():
        if isinstance(channel, Channel):
            if aq_base(channel.collector) is aq_base(collector):
                channel.collector = None

# This lists of factories is mutable: You can add to it:
channels = [Channel,]
