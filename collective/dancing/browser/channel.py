import datetime
import sys

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
from collective.dancing import collector
from collective.dancing import utils
from collective.dancing.channel import Channel
from collective.dancing.browser import controlpanel

def simpleitem_wrap(klass, name):
    class SimpleItemWrapper(klass, OFS.SimpleItem.SimpleItem):
        __doc__ = OFS.SimpleItem.SimpleItem.__doc__
        id = name
        def Title(self):
            return klass.title

    klassname = klass.__name__
    SimpleItemWrapper.__name__ = klassname
    module = sys.modules[__name__]
    assert not hasattr (module, klassname), "%r already a name in this module."
    setattr(module, klassname, SimpleItemWrapper)
    return SimpleItemWrapper

schedulers = [
    simpleitem_wrap(klass, 'scheduler')
    for klass in collective.singing.scheduler.schedulers]

class FactoryChoice(schema.Choice):
    def _validate(self, value):
        if self._init_field:
            return
        super(schema.Choice, self)._validate(value)

        # We'll skip validating against the vocabulary

def scheduler_vocabulary(context):
    terms = []
    for factory in schedulers:
        terms.append(
            zope.schema.vocabulary.SimpleTerm(
                value=factory(),
                token='%s.%s' % (factory.__module__, factory.__name__),
                title=factory.title))
    return utils.LaxVocabulary(terms)
zope.interface.alsoProvides(scheduler_vocabulary,
                            zope.schema.interfaces.IVocabularyFactory)

class ManageChannelsForm(crud.CrudForm):
    """Crud form for channels.
    """
    @property
    def update_schema(self):
        fields = field.Fields(IChannel).select('title')

        collector = schema.Choice(
            __name__='collector',
            title=IChannel['collector'].title,
            vocabulary='Collector Vocabulary')

        scheduler = FactoryChoice(
            __name__='scheduler',
            title=IChannel['scheduler'].title,
            vocabulary='Scheduler Vocabulary')

        fields += field.Fields(collector, scheduler)
        return fields

    @property
    def view_schema(self):
        return self.update_schema.copy()
    
    def get_items(self):
        return [(ob.getId(), ob) for ob in self.context.objectValues()]
    
    def add(self, data):
        name = Products.CMFPlone.utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        self.context[name] = Channel(
            name, data['title'], data['collector'], data['scheduler'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field):
        if field == 'title':
            return item.absolute_url()
        elif field == 'collector':
            return item.collector.absolute_url()
        elif field == 'scheduler':
            if item.scheduler is not None:
                return item.scheduler.absolute_url()

class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')
    
    label = _(u'Newsletter Channels administration')
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return ManageChannelsForm(self.context.channels, self.request)()

class ManageSubscriptionsForm(crud.CrudForm):
    """Crud form for subscriptions.
    """
    # These are set by the SubscriptionsAdministrationView
    format = None 
    composer = None

    @property
    def prefix(self):
        return self.format

    def _composer_fields(self):
        return field.Fields(self.composer.schema)

    def _collector_fields(self):
        return field.Fields(self.context.collector.schema)

    @property
    def update_schema(self):
        fields = self._composer_fields()
        fields += self._collector_fields()
        return fields

    def get_items(self):
        subscriptions = collective.singing.interfaces.ISubscriptions(
            self.context)
        items = []
        for secret, subscriptions in subscriptions.items():
            for subscription in subscriptions:
                md = collective.singing.interfaces.ISubscriptionMetadata(
                    subscription)
                if md['format'] == self.format:
                    items.append((secret, subscription))
        return items

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
        self.context.manage_delObjects([id])

class SubscriptionChoiceFieldDataManager(z3c.form.datamanager.AttributeField):
    # This nasty hack allows us to have the default IDataManager to
    # use a different schema for adapting the context.  This is
    # necessary because the schema that
    # ``collector.SmartFolderCollector.schema`` produces is a
    # dynamically generated interface.
    #
    # ``collector.SmartFolderCollector.schema`` should rather produce
    # an interface with fields that already have the right interface
    # to adapt to as their ``interface`` attribute.
    component.adapts(
        collective.singing.subscribe.SimpleSubscription,
        zope.schema.interfaces.IField)

    def __init__(self, context, field):
        super(SubscriptionChoiceFieldDataManager, self).__init__(context, field)
        if self.field.interface is not None:
            if issubclass(self.field.interface, collector.ICollectorSchema):
                self.field.interface = collector.ICollectorSchema

class SubscriptionsAdministrationView(BrowserView):
    """Manage subscriptions in a channel.
    """
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'"${channel}" subscriptions administration',
                 mapping=dict(channel=self.context.title))

    def back_link(self):
        return dict(label=_(u"Up to Channels administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())

    def contents(self):
        z2.switch_on(self)
        forms = []
        for format, composer in self.context.composers.items():
            form = ManageSubscriptionsForm(self.context, self.request)
            form.format = format
            form.composer = composer
            forms.append(form)
        return '\n'.join([form() for form in forms])
