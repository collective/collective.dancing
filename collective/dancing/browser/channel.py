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
from zope.app.pagetemplate import viewpagetemplatefile
from collective.dancing import MessageFactory as _
from collective.dancing import collector
from collective.dancing import utils
from collective.dancing.channel import Channel
from collective.dancing.browser import controlpanel
from collective.dancing.browser import widget

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

class ChannelEditForm(crud.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('channel-crud-table.pt')
    def _update_subforms(self):
        self.subforms = []
        for id, item in self.context.get_items():
            subform = ChannelEditSubForm(self, self.request)
            subform.content = item
            subform.content_id = id
            subform.update()
            self.subforms.append(subform)

class ChannelEditSubForm(crud.EditSubForm):
    """special version of get titles for channel"""
    template = viewpagetemplatefile.ViewPageTemplateFile('channel-crud-row.pt')
    def getNiceTitles(self):
        widgetsForTitles = self.getTitleWidgets()        

        freakList = []
        for item in widgetsForTitles:
            freakList.append(item.field.title)
        if len(freakList)> 2:
            freakList[2] = u'Subscribers'
        return freakList

class ManageChannelsForm(crud.CrudForm):
    """Crud form for channels.
    """
    
    description = _("Add or edit channels that will use collectors to gather and email specific sets of information from your site, to subscribed email addresses, at scheduled times.")
    editform_factory = ChannelEditForm
    template = viewpagetemplatefile.ViewPageTemplateFile('channel-form-master.pt')
    @property
    def update_schema(self):
        fields = field.Fields(IChannel).select('title')

        collector = schema.Choice(
            __name__='collector',
            title=IChannel['collector'].title,
            required=False,
            vocabulary='Collector Vocabulary')

        scheduler = FactoryChoice(
            __name__='scheduler',
            title=IChannel['scheduler'].title,
            required=False,
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
            name, data['title'],
            collector=data['collector'],
            scheduler=data['scheduler'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field):
        if field == 'title':
            return item.absolute_url()
        elif field == 'collector' and item.collector is not None:
            collector_id = item.collector.getId()
            collector = getattr(self.context.aq_inner.aq_parent.collectors,
                                collector_id)
            return collector.absolute_url()
        elif field == 'scheduler':
            if item.scheduler is not None:
                return item.scheduler.absolute_url()

class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')
    
    label = _(u'Channel administration')
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
        if self.context.collector is not None:
            return field.Fields(self.context.collector.schema)
        return field.Fields()

    @property
    def update_schema(self):
        fields = self._composer_fields()
        fields += self._collector_fields()
        return fields

    def get_items(self):
        subscriptions = self.context.subscriptions
        items = []
        for name, subscription in subscriptions.items():
            if subscription.metadata['format'] == self.format:
                items.append((str(name), subscription))
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

        return self.context.subscriptions.add_subscription(
            self.context, secret, composer_data, collector_data, metadata)

    def remove(self, (id, item)):
        key, format = id.rsplit('-', 1)
        subs = self.context.subscriptions.query(key=key, format=format)
        for subscription in subs:
            self.context.subscriptions.remove_subscription(subscription)

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

class EditChannelForm(z3c.form.form.EditForm):
    """ """
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    heading = _(u"Edit Channel")

    @property
    def fields(self):
        fields = z3c.form.field.Fields(IChannel).select('title',
                                                        'description')
        fields['description'].widgetFactory[
            z3c.form.interfaces.INPUT_MODE] = widget.WysiwygFieldWidget

        collector = schema.Choice(
            __name__='collector',
            title=IChannel['collector'].title,
            required=False,
            vocabulary='Collector Vocabulary')

        scheduler = FactoryChoice(
            __name__='scheduler',
            title=IChannel['scheduler'].title,
            required=False,
            vocabulary='Scheduler Vocabulary')
        
        fields += field.Fields(collector, scheduler)
        return fields

class ChannelEditView(BrowserView):
    """Dedicated Edit page for channels
       As opposed to the crud form this
       allows editing of all channel settings
       """
    
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    @property
    def back_link(self):
        return dict(label=_(u"Up to Channels administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())


    @property
    def label(self):
        return _(u'Edit Channel ${channel}',
                 mapping={'channel':self.context.Title()})

    def contents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return EditChannelForm(self.context, self.request)()
