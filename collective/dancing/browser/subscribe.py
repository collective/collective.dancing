from zope import component
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import collective.singing.interfaces
import collective.singing.z2
import collective.singing.browser.subscribe

from collective.dancing import MessageFactory as _

class Subscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')

    label = _(u"Subscribe")

    def __call__(self):
        collective.singing.z2.switch_on(self)
        return self.template()

    def contents(self):
        subscribe = collective.singing.browser.subscribe.Subscribe(
            self.context.aq_inner, self.request)
        return subscribe()

class Confirm(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Confirming your subscription")

    def __call__(self):
        secret = self.request.form['secret']
        subscriptions = self.context.aq_inner.subscriptions

        if secret in subscriptions:
            for subscription in subscriptions[secret]:
                m = collective.singing.interfaces.ISubscriptionMetadata(
                    subscription)
                m['pending'] = False
            self.status = _(u"You confirmed your subscription successfully.")
        else:
            self.status = _(u"Your subscription isn't known to us.")

        return self.template()

class Unsubscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Unsubscribe")

    def __call__(self):
        secret = self.request.form['secret']
        subscriptions = self.context.aq_inner.subscriptions
        
        if secret in subscriptions:
            del subscriptions[secret]
            self.status = _(u"You unsubscribed successfully.")
        else:
            self.status = _(u"You aren't subscribed to this channel.")

        return self.template()
