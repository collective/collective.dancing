from Acquisition import aq_base

import collective.singing.subscribe
from collective.singing.interfaces import ISubscriptions
import zope.interface
import persistent.dict

from Products.CMFCore.utils import getToolByName
from collective.singing.subscribe import SimpleSubscription

from OFS.SimpleItem import SimpleItem

from copy import copy

import logging
logger = logging.getLogger('collective.dancing')


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


dummy_collector = object()


class SubscriptionFromDictionary(SimpleSubscription):
    """
      A transiant subscription object. Turns a dictionary into a subscription.
    """

    def find_topic(self, title):
        collector = self._channel.collector
        if not collector:
            return None

        selected_collector = collector.id
        collectors = self._channel.collectors
        if selected_collector not in collectors.keys():
            return None

        logger.debug("collectors[selected_collector] %s" %
                    (type(collectors[selected_collector])))
        if not collectors[selected_collector]:
            return None

        optional_collectors = collectors[selected_collector]. \
            get_optional_collectors()
        for optional in optional_collectors:
            # make sure both are same format
            if unicode(optional.title) == unicode(title):
                return optional
        return None

    def __init__(self, channel, data):

        self._channel = channel

        collector_data = copy(data["collector_data"])

        selected_collectors = []
        # introduce subscribe_collectors for custom channel that
        # don't use the default collector
        subscribe_collectors = data["collector_data"]["selected_collectors"]
        for collector_title in subscribe_collectors:
            try:
                collector = self.find_topic(collector_title)
            except AttributeError:
                collector = None
            if collector is not None:
                selected_collectors.append(collector)

        if not selected_collectors:
            # if selected_collectors is empty it is important to leave it empty
            # even though some channels don't have optional sections.
            # In a channel with optional sections a missing selected_collectors
            # means subscriber will get everything
            # An empty selected_collectors means they will get nothing.
            # we want the latter.
            selected_collectors = [dummy_collector]

        collector_data["subscribe_collectors"] = set(subscribe_collectors)
        collector_data["selected_collectors"] = set(selected_collectors)

        composer_data = copy(data["composer_data"])
        metadata = copy(data["metadata"])

        # make sure the composer_data email is unicode too
        subscription_email = unicode(composer_data["email"])
        composer_data["email"] = subscription_email

        super(SubscriptionFromDictionary, self).__init__(
            channel,
            data["secret"],
            composer_data,
            collector_data,
            metadata
        )

        # S&D expects to have a persistent store during send to store the
        # cue for example. It stores it in self.metadata. We will instead
        # replace it with a store in the channel object itself.
        if subscription_email not in self._channel.subscriptions_metadata:
            self._channel.subscriptions_metadata[subscription_email] = \
                persistent.dict.PersistentDict()
            # we only set the metadata the first time from the subscriber list.
            # We don't want to keep creating commits on sends
            self._channel.subscriptions_metadata[subscription_email]. \
                update(metadata)

        self.metadata = self._channel.subscriptions_metadata[subscription_email]


class SubscriptionsFromScript (SimpleItem):
    """
        Call a script within the portal to get a list of subscriptions.
        Each subscription is a dictionary which is transiantly converted
        using SubscriptionFromDictionary
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

        #HACK: This needs to change to a much simpler format compatible with
        # plone gazette.
        # ie [(email, html, changeUrl), ...]
        # or [(email, html, changeUrl, {"name":"me"...}), ...]
        # or [(email, html, changeUrl, {"name":"me"...},
        # ['jobs','news',...]), ...]

        if channel.script_path is not None:
            # HACK: Why aren't we using a tal expression like plone gazette?
            script = portal.unrestrictedTraverse(str(channel.script_path))
            # HACK: Why are we silently dropping subscribers?
            for item in script():
                # check the script have right data
                # data have "composer_data", "secret", "collector_data",
                # and "metadata"
                if "composer_data" not in item:
                    continue
                if "email" not in item["composer_data"]:
                    continue
                # HACK: Why does secret have to be here?
                # We need a unsubscribe link instead
                if "secret" not in item:
                    continue
                if "collector_data" not in item:
                    continue
                if "selected_collectors" not in item["collector_data"]:
                    continue
                if "metadata" not in item:
                    continue
                yield SubscriptionFromDictionary(channel, item)

    def add_subscription(self, channel, secret, composer_data,
                         collector_data, metadata):
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
