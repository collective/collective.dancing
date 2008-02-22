import datetime

from zope import component
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

    @property
    def label(self):
        return _(u'Edit ${format} ${composer}', mapping={'format':self.format,
                                                         'composer':self.composer.name})
    
    @property
    def prefix(self):
        return self.context.name + self.format

    def _composer_fields(self):
        return field.Fields(self.composer.schema)

    def _collector_fields(self):
        return field.Fields(self.context.collector.schema)

    @property
    def update_schema(self):
        fields = self._composer_fields()
        fields += self._collector_fields()
        return fields

    def update(self):
        super(SubscriptionsOverviewForm, self).update()

        subscriptions = collective.singing.interfaces.ISubscriptions(
            self.context)
        secret = self.request.get('secret', None) 
        if (secret and subscriptions[secret]):
            editform = self.editform_factory(self, self.request)
            editform.update()
            self.subforms = [editform]
        else:
            addform = self.addform_factory(self, self.request)
            addform.update()
            self.subforms = [addform]


    def get_items(self):
        subscriptions = collective.singing.interfaces.ISubscriptions(
            self.context)

        secret = self.request.get('secret', None) 

        my_subscriptions = subscriptions[secret]
        items = []
        
        for subscription in my_subscriptions:
            items.append(('%s:%s:%s' %
                          (secret, self.format, self.name), subscription))
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
        secret, format, channel= id.rsplit(':', 2)
        user_subscriptions = self.context.subscriptions[secret]
        for_format = [s for s in user_subscriptions
                      if s.metadata['format'] == format]
        #assert len(for_format) == 1
        for_format = for_format[0]
        user_subscriptions.remove(for_format)


        
class SubscriptionsOverviewView(BrowserView):
    """Manage subscriptions in a channel.
    """
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Subscriptions administration',
                 mapping=dict(channel=self.context.title))

    def back_link(self):
        return dict(label=_(u"Back to Channels administration"),
                    url=self.context.absolute_url())

    def contents(self):
        z2.switch_on(self)
        forms = []
        
        for channel in component.getUtility(collective.singing.interfaces.IChannelLookup)():
            for format, composer in channel.composers.items():
                request = self.request
                request['secret'] = collective.singing.subscribe.secret(
                    channel, composer, {'email':u'daniel@localhost'}, request)

                form = SubscriptionsOverviewForm(channel, request)
                #format, composer = channel.composers.items()[0] #Only one composer for now!
                form.format = format
                form.composer = composer
                forms.append(form)
        return '\n'.join([form() for form in forms])
