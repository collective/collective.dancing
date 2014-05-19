# -*- coding: utf-8 -*-
import zope.component.interfaces
from zope.interface import implements


class IConfirmSubscriptionEvent(zope.component.interfaces.IObjectEvent):
    """A subscription has been confirmed"""


class ConfirmSubscriptionEvent(zope.component.interfaces.ObjectEvent):
    """A subscription has been confirmed"""
    implements(IConfirmSubscriptionEvent)

    def __init__(self, channel, subscription):
        super(ConfirmSubscriptionEvent, self).__init__(channel)
        self.subscription = subscription


class IConfirmUnsubscriptionEvent(zope.component.interfaces.IObjectEvent):
    """A subscription has been removed"""


class ConfirmUnsubscriptionEvent(zope.component.interfaces.ObjectEvent):
    """A subscription has been removed"""
    implements(IConfirmUnsubscriptionEvent)
