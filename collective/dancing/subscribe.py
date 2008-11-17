from Acquisition import aq_base

import collective.singing.subscribe

class Subscription(collective.singing.subscribe.SimpleSubscription):
    _channel = None
    @apply
    def channel():
        def get(self):
            if self._channel is not None:
                # We want to get the same channel from the
                # ``channel_lookup`` as that has the correct wrapping:
                for channel in collective.singing.channel.channel_lookup():
                    if aq_base(channel) is aq_base(self._channel):
                        return channel
            return self._channel
        def set(self, channel):
            self._channel = channel
        return property(get, set)

class Subscriptions(collective.singing.subscribe.Subscriptions):
    subscription_factory = Subscription
