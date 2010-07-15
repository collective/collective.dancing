from Acquisition import aq_base

import collective.singing.subscribe

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
