import random
import string
from UserString import UserString

from zope import component
from zope import interface
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
import collective.dancing.collector
import collective.dancing.composer
import collective.dancing.subscribe
import collective.dancing.utils
from collective.dancing import MessageFactory as _

def portal_newsletters():
    """Return channels created with the newsletter tool."""

    root = component.queryUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    if root is None:
        return []
    root = collective.dancing.utils.fix_request(root, 0)
    channels = root['portal_newsletters']['channels'].objectValues()
    security = AccessControl.getSecurityManager()
    return [c for c in channels if security.checkPermission('View', c)]

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

class IPortalNewsletters(interface.Interface):
    pass

class PortalNewsletters(OFS.Folder.Folder):
    interface.implements(IPortalNewsletters)

    def Title(self):
        return u"Newsletters"


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
    salt = Salt()
    sm = zope.app.component.hooks.getSite().getSiteManager()
    tool.salt = salt
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

    Title = u"Channels"

@component.adapter(IChannelContainer,
                   zope.app.container.interfaces.IObjectAddedEvent)
def channels_added(container, event):
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

    def __init__(self, name, title=None, composers=None,
                 collector=None, scheduler=None, description=u""):
        self.name = name
        if title is None:
            title = name
        self.title = title
        self.description = description
        self.subscriptions = collective.dancing.subscribe.Subscriptions()
        if composers is None:
            composers = {'html': collective.dancing.composer.HTMLComposer()}
        self.composers = composers
        self.collector = collector
        self.scheduler = scheduler
        self.queue = collective.singing.message.MessageQueues()
        super(Channel, self).__init__(name)

    @property
    def id(self):
        return self.name

    def Title(self):
        return self.title

@component.adapter(collective.singing.interfaces.ICollector,
                   zope.app.container.interfaces.IObjectRemovedEvent)
def collector_removed(collector, event):
    for channel in collective.singing.channel.channel_lookup():
        if isinstance(channel, Channel):
            if aq_base(channel.collector) is aq_base(collector):
                channel.collector = None
