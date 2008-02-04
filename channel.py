from zope import component
from zope import interface
import zope.app.container.interfaces

import OFS.event
import OFS.Folder
import OFS.SimpleItem
import Products.CMFPlone.interfaces
import collective.singing.subscribe
import collective.singing.interfaces
import collective.singing.message

import collective.dancing.collector

def channel_lookup():
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return root['portal_newsletters']['channels'].objectValues()
interface.directlyProvides(channel_lookup,
                           collective.singing.interfaces.IChannelLookup)

class PortalNewsletters(OFS.Folder.Folder):
    pass

@component.adapter(PortalNewsletters,
                   zope.app.container.interfaces.IObjectAddedEvent)
def tool_added(tool, event):
    factories = dict(channels=ChannelContainer,
                     collectors=collective.dancing.collector.CollectorContainer)
    existing = tool.objectIds()
    for name, factory in factories.items():
        if name not in existing:
            tool[name] = factory(name)

class ChannelContainer(OFS.Folder.Folder):
    """
      >>> container = ChannelContainer('xs')
      >>> container['your-channel'] = Channel('wq')
      >>> container.objectIds()
      ['your-channel']
    """

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

    def __init__(self, name, title=None):
        self.name = name
        if title is None:
            title = name
        self.title = title
        self.subscriptions = collective.singing.subscribe.SimpleSubscriptions()
        self.composers = None
        self.collector = None
        self.scheduler = None
        self.queue = collective.singing.message.MessageQueues()
        super(Channel, self).__init__(name)

    @property
    def id(self):
        return self.name
