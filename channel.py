from zope import component
from zope import interface

import OFS.Folder
import OFS.SimpleItem
import Products.CMFPlone.interfaces

import collective.singing.subscribe
import collective.singing.interfaces


def channel_lookup():
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return root['newsletter-channels'].objectValues()
interface.directlyProvides(channel_lookup,
                           collective.singing.interfaces.IChannelLookup)


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
    """
    interface.implements(collective.singing.interfaces.IChannel)

    def __init__(self, name):
        self.name = name
        self.subscriptions = collective.singing.subscribe.SimpleSubscriptions()
        self.composers = None
        self.collector = None
        self.scheduler = None

    @property 
    def id(self):
        return self.name

