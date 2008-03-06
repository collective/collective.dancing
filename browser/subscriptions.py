import datetime

from zope import component
from zope import interface
from zope import schema
import zope.interface
import zope.schema.interfaces
import zope.schema.vocabulary
from z3c.form import field
import z3c.form.interfaces
import z3c.form.datamanager
import z3c.form.term
import OFS.SimpleItem
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import Products.CMFPlone.utils
from collective.singing.interfaces import IChannel
from collective.singing import z2
from collective.singing.browser import crud
import collective.singing.scheduler
import collective.singing.subscribe

from collective.dancing import MessageFactory as _

class SubscriptionsOverviewForm(crud.CrudForm):
    """Crud form for subscriptions.
    """
    # These are set by the SubscriptionsAdministrationView
    format = None 
    composer = None


    # No add form yet
    addform_factory = crud.NullForm
    
    @property
    def label(self):
        return _(u'Edit ${format} ${composer}', mapping={'format':self.format,
                                                         'composer':self.composer.name})
    
    @property
    def prefix(self):
        return str(self.context.Title + self.format)

    def _composer_fields(self):
        return field.Fields(self.composer.schema)

    def _collector_fields(self):
        return []
        return field.Fields(self.context.collector.schema)

    @property
    def update_schema(self):
        return None # we're using IUpdateSchema adapter

    def add_schema(self):
        return None

    def get_items(self):
        items = []
        for channel in component.getUtility(collective.singing.interfaces.IChannelLookup)():
             subscriptions = collective.singing.interfaces.ISubscriptions(channel)
             secret = collective.singing.subscribe.secret(
                          channel,
                          channel.composers[self.request.get('format')],
                          {'email':self.request.get('email', '')},
                          self.request)

             my_subscriptions = subscriptions[secret]
             for secret, subscriptions in subscriptions.items():
                 for subscription in subscriptions:
                     md = collective.singing.interfaces.ISubscriptionMetadata(
                         subscription)
                     if md['format'] == self.format:
                         items.append(('%s:%s:%s' %
                               (secret, self.format, channel.name), subscription))
        return items
        #for secret, subscriptions in list(subscriptions[secret]):
        #    for subscription in subscriptions:
        #        md = collective.singing.interfaces.ISubscriptionMetadata(
        #            subscription)
        #        if md['format'] == self.format:
        #            items.append(('%s:%s' %
        #                          (secret, self.format), subscription))
        #return items

    def add(self, data):
        secret = collective.singing.subscribe.secret(
            self.context, self.composer, data, self.request)

        composer_data = dict(
            [(name, value) for (name, value) in data.items()
             if name in self._composer_fields()])

        collector_data = dict(
            [(name, value) for (name, value) in data.items()
             if name in self._collector_fields()])

        metadata = dict(format=self.format,
                        date=datetime.datetime.now())

        subscription = collective.singing.subscribe.SimpleSubscription(
            self.context, secret, composer_data, collector_data, metadata)

        subscriptions = collective.singing.interfaces.ISubscriptions(
            self.context)
        subscriptions[secret].append(subscription)
        return subscription

    def remove(self, (id, item)):
        secret, format, channelname = id.rsplit(':', 2)

        for channel in component.getUtility(collective.singing.interfaces.IChannelLookup)():
            if channel.name == channelname:
                user_subscriptions = channel.subscriptions[secret]
                for_format = [s for s in user_subscriptions
                              if s.metadata['format'] == format]
                assert len(for_format) == 1
                for_format = for_format[0]
                user_subscriptions.remove(for_format)

@component.adapter(SubscriptionsOverviewForm, collective.singing.interfaces.ISubscription)
@interface.implementer(crud.IUpdateSchema)
def subscriptionsoverview_updatefields(form, subscription):
    collector_schema = subscription.channel.collector.schema
    return field.Fields(collector_schema)

class ISubscriptionOverviewViewSchema(interface.Interface):
    channelname = schema.TextLine(title=_(u'Channel'))
                           
@component.adapter(SubscriptionsOverviewForm, collective.singing.interfaces.ISubscription)
@interface.implementer(crud.IViewSchema)
def subscriptionsoverview_viewfields(form, subscription):
    return field.Fields(field)
    
class SubscriptionsOverviewView(BrowserView):
    """Manage subscriptions in a channel.
    """
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Your subscriptions',
                 mapping=dict(channel=self.context.title))

    def contents(self):
        z2.switch_on(self)
        forms = []
        composers = component.getUtility(collective.singing.interfaces.IChannelLookup)()[0].composers
        for format, composer in composers.items():
            request = self.request
            request.set('format',format) 

            form = SubscriptionsOverviewForm(self.context, request)

            form.format = format
            form.composer = composer
            forms.append(form)
        return '\n'.join([form() for form in forms])

