from zope import component
from zope import interface
import zope.app.container.interfaces

from Acquisition import aq_base
import OFS.event
import OFS.Folder
import OFS.SimpleItem
import Products.CMFPlone.interfaces
import collective.singing.subscribe
import collective.singing.interfaces
import collective.singing.message

import collective.dancing.collector
import collective.dancing.composer
from collective.dancing import MessageFactory as _

def channel_lookup():
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return root['portal_newsletters']['channels'].objectValues()
interface.directlyProvides(channel_lookup,
                           collective.singing.interfaces.IChannelLookup)

def channel_vocabulary(context):
    terms = []
    for channel in channel_lookup():
        req = context.aq_chain[-1]
        tmp = req
        for item in reversed(channel.aq_chain):
            tmp = aq_base(item).__of__(tmp)
        channel = tmp
        terms.append(
            zope.schema.vocabulary.SimpleTerm(
                value=channel,
                token=channel.name,
                title=channel.title))
    return zope.schema.vocabulary.SimpleVocabulary(terms)
interface.alsoProvides(channel_vocabulary,
                       zope.schema.interfaces.IVocabularyFactory)

class IPortalNewsletters(interface.Interface):
    pass

class PortalNewsletters(OFS.Folder.Folder):
    interface.implements(IPortalNewsletters)
    Title = u"Newsletters"

@component.adapter(IPortalNewsletters,
                   zope.app.container.interfaces.IObjectAddedEvent)
def tool_added(tool, event):
    factories = dict(channels=ChannelContainer,
                     collectors=collective.dancing.collector.CollectorContainer)
    existing = tool.objectIds()
    for name, factory in factories.items():
        if name not in existing:
            tool[name] = factory(name)

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
#    mega_broadcast_channel = MetaChannel('mega_broadcast_channel', title=_(u"Mega broadcast"))
#    container['mega_broadcast_channel'] = mega_broadcast_channel

class Channel(OFS.SimpleItem.SimpleItem):
    """
      >>> channel = Channel('xs')
      >>> from zope.interface.verify import verifyObject
      >>> verifyObject(collective.singing.interfaces.IChannel, channel)
      True
      >>> channel.name
      'xs'
      """    
    interface.implements(collective.singing.interfaces.IChannel, 
                         collective.singing.interfaces.ISimpleChannel)

    def __init__(self, name, title=None,
                 composers=None, collector=None, scheduler=None):
        self.name = name
        if title is None:
            title = name
        self.title = title
        self.subscriptions = collective.singing.subscribe.SimpleSubscriptions()
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


class MetaChannel(OFS.SimpleItem.SimpleItem):
    """
      >>> metachannel =MetaChannel('mc')
      >>> from zope.interface.verify import verifyObject
      >>> verifyObject(collective.singing.interfaces.IMetaChannel, metachannel)
      True
      >>> metachannel.name
      'mc'
    """
    interface.implements(collective.singing.interfaces.IChannel,
                         collective.singing.interfaces.IMetaChannel)
    def __init__(self, name, title=None,
                 composers=None, collector=None, scheduler=None):
        self.name = name
        if title is None:
            title = name
        self.title = title
        self.subscriptions = collective.singing.subscribe.MetaSubscriptions()
        if composers is None:
            composers = {'html': collective.dancing.composer.HTMLComposer()}
        self.composers = composers
        self.collector = collector
        self.scheduler = scheduler
        self.queue = collective.singing.message.MessageQueues()
        super(MetaChannel, self).__init__(name)

    @property
    def id(self):
        return self.name

    def Title(self):
        return self.title    
    
@component.adapter(MetaChannel)
@interface.implementer(collective.singing.interfaces.ISubscriptions)
def metachannel_subscriptions(channel):
    return channel.subscriptions    
        
@component.adapter(Channel)
@interface.implementer(collective.singing.interfaces.ISubscriptions)
def channel_subscriptions(channel):
    return channel.subscriptions
