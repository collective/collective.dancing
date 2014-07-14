from Acquisition import aq_base

import collective.singing.subscribe
from collective.singing.interfaces import ISubscriptions, ISubscription
import zope.interface
from Persistence import Persistent

from Products.CMFCore.utils import getToolByName
from collective.singing.subscribe import SimpleSubscription

from OFS.SimpleItem import SimpleItem
from collective.singing.channel import channel_lookup

from copy import copy

class Subscription(collective.singing.subscribe.SimpleSubscription):
    _channel = None
    @apply
    def channel():
        def get(self):
            if self._channel is not None:
                all_channels = list(collective.singing.channel.channel_lookup())
                # We want to get the same channel from the
                # ``channel_lookup`` as that has the correct wrapping:
                for channel in all_channels:
                    if aq_base(channel) is aq_base(self._channel):
                        return channel

                # Our channel doesn't exist!  Look for a channel with
                # the same name:
                for channel in all_channels:
                    if channel.name == self._channel.name:
                        self._channel = channel
                        return channel

            raise AttributeError(
                "%r is subscribed to unknown mailing-list %r" % self._channel)

        def set(self, channel):
            self._channel = channel
        return property(get, set)


class Subscriptions(collective.singing.subscribe.Subscriptions):
    subscription_factory = Subscription


class SubscriptionFromDictionary (SimpleSubscription):
    """
      A transiant subscription object. Turns a dictionary into a subscription.
    """

    def find_topic(self, title):
        collector = self._channel.collector
        optional_collectors = collector.get_optional_collectors()
        for c in optional_collectors:
            if c.title == title:
                return c
        return None

    def __init__(self, channel, data):

        self._channel = channel
        
        collector_data = copy(data["collector_data"])

        collector_data["selected_collectors"] = []
        for collector_title in data["collector_data"]["selected_collectors"]:
            collector = self.find_topic(collector_title)
            if collector is not None:
                collector_data["selected_collectors"].append(collector)

        super(SubscriptionFromDictionary, self).__init__(
            channel,
            data['secret'],
            copy(data["composer_data"]),
            collector_data,
            copy(data["metadata"])
        )


class SubscriptionsFromScript (SimpleItem):
    """
        Call a script within the portal to get a list of subscriptions. Each subscription
        is a dictionary which is transiantly converted using SubscriptionFromDictionary
    """
    
    zope.interface.implements(ISubscriptions)

    def __init__(self):
        super(SubscriptionsFromScript, self).__init__()

    def get_channel(self):
        return self.aq_parent

    def values(self):
        """Iterate over all subscription objects.
        """

        channel = self.get_channel()
        portal = getToolByName(channel, "portal_url").getPortalObject()

        if channel.script_path is not None:
            script = portal.unrestrictedTraverse(str(channel.script_path))
            for item in script():
                yield SubscriptionFromDictionary(channel, item)

    def add_subscription(self, channel, secret, composer_data, collector_data, metadata):
        """Add a subscription and return it.

        Raises ValueError if subscription already exists.
        """
        raise NotImplementedError()

    def remove_subscription(self, subscription):
        """Remove subscription.
        """
        raise NotImplementedError()

    def query(self, **kwargs):
        """Search subscriptions.

        Available fields are: 'fulltext', 'secret', 'format', 'key', 'label'.
        """
        return []
