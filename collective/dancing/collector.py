from zope import component
from zope import interface
from zope import schema
import zope.interface.interface
import zope.schema.vocabulary
import zope.schema.interfaces
import zope.app.container.interfaces
import zope.i18nmessageid
import Acquisition
import DateTime
import OFS.Folder
import persistent
import persistent.wref
import persistent.list

import z3c.form.field
import z3c.formwidget.query.interfaces
import Products.CMFCore.utils
import Products.CMFPlone.interfaces
import Products.CMFPlone.utils
from Products.ATContentTypes.content.topic import ATTopic
import collective.singing.interfaces

from collective.dancing import utils
from collective.dancing import MessageFactory as _

def collector_vocabulary(context):
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    collectors = root['portal_newsletters']['collectors'].objectValues()
    terms = []
    for collector in collectors:
        terms.append(
            zope.schema.vocabulary.SimpleTerm(
                value=collector,
                token='/'.join(collector.getPhysicalPath()),
                title=collector.title))
    return zope.schema.vocabulary.SimpleVocabulary(terms)
interface.alsoProvides(collector_vocabulary,
                       zope.schema.interfaces.IVocabularyFactory)

class CollectorContainer(OFS.Folder.Folder):
    title = u"Collectors"

    def Title(self):
        return self.title


@component.adapter(CollectorContainer,
                   zope.app.container.interfaces.IObjectAddedEvent)
def container_added(container, event):
    name = 'default-latest-news'
    if name in container.objectIds():
        return
    container[name] = Collector(
        name, container.translate(_(u'Latest news')))
    topic = container[name].objectValues()[0]
    type_crit = topic.addCriterion('Type', 'ATPortalTypeCriterion')
    type_crit.setValue('News Item')
    sort_crit = topic.addCriterion('created', 'ATSortCriterion')
    state_crit = topic.addCriterion('review_state',
                                    'ATSimpleStringCriterion')
    state_crit.setValue('published')
    topic.setSortCriterion('created', True)
    topic.setLayout('folder_summary_view')

@component.adapter(collective.singing.interfaces.ISubscription)
@interface.implementer(collective.singing.interfaces.ICollectorSchema)
def collectordata_from_subscription(subscription):
    return utils.AttributeToDictProxy(subscription.collector_data)

class ITextCollector(collective.singing.interfaces.ICollector):
    value = schema.Text(title=_(u'Rich text'))

class TextCollector(OFS.SimpleItem.SimpleItem):
    interface.implements(ITextCollector)
    significant = False
    title = _(u'Rich text')
    value = u''

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def get_items(self, cue=None, subscription=None):
        return [self.value], None

class IReferenceCollector(collective.singing.interfaces.ICollector):
    items = interface.Attribute(
        """Weak references.""")

class ReferenceCollector(OFS.SimpleItem.SimpleItem):
    interface.implements(IReferenceCollector)
    title = _(u'Content selection')
    items = ()

    def __init__(self, id, title):
        self.id = id
        self.title = title

    def get_items(self, cue=None, subscription=None):
        items = self._rebuild_items()
        return tuple(items), None

    def _rebuild_items(self):
        catalog = Products.CMFCore.utils.getToolByName(self, 'portal_catalog')

        for ref in self.items:
            if not isinstance(ref, persistent.wref.WeakRef):
                raise ValueError(_(u"Must be a weak reference (got ${title})", mapping={'title': repr(ref)}))

            item = ref()

            if item is not None:
                uid = item.UID()

                try:
                    brain = catalog(UID=uid)[0]
                except IndexError:
                    continue

                yield brain.getObject()

class Collector(OFS.Folder.Folder):
    interface.implements(collective.singing.interfaces.ICollector)
    title = _(u'Collector block')

    def __init__(self, id, title):
        self.id = id
        self.title = title
        self.optional = False
        super(Collector, self).__init__()

    def Title(self):
        return self.title

    def get_items(self, cue=None, subscription=None):
        now = DateTime.DateTime()

        # Don't return items if we're optional and not selected:
        if self.optional:
            if subscription is not None:
                sdata = subscription.collector_data
                name = 'selected_collectors'
                if name in sdata and sdata[name] and self not in sdata[name]:
                    return [], now

        # If no ``significant`` children return any items, we'll
        # return the empty list.
        significant = False
        items = []

        for child in self.objectValues():
            if isinstance(child, ATTopic):
                l = self.get_items_for_topic(child, cue)
                if l:
                    significant = True
                items.extend(l)
            else:
                l = child.get_items(cue, subscription)[0]
                if l and getattr(child, 'significant', True):
                    significant = True
                items.extend(l)

        return significant and items or [], now

    @staticmethod
    def get_items_for_topic(topic, cue):
        query_args = {}
        if cue is not None and topic.hasSortCriterion():
            sort_criterion = topic.getSortCriterion()
            fname = str(sort_criterion.field)
            query_factory = sort_criteria.get(
                fname, sort_criteria.get('default'))
            query_args[fname] = query_factory(cue)
        return topic.queryCatalog(full_objects=True, **query_args)

    def get_optional_collectors(self):
        optional_collectors = []
        if self.optional:
            optional_collectors.append(self)
        for child in self.objectValues():
            if collective.singing.interfaces.ICollector.providedBy(child):
                if hasattr(
                    Acquisition.aq_base(child), 'get_optional_collectors'):
                    optional_collectors.extend(child.get_optional_collectors())
                elif getattr(Acquisition.aq_base(child), 'optional', False):
                    optional_collectors.append(child)

        return optional_collectors

    def get_next_id(self):
        if self._objects:
            return str(max([int(info['id']) for info in self._objects]) + 1)
        else:
            return '0'

    @property
    def schema(self):
        fields = []

        optional_collectors = self.get_optional_collectors()
        if optional_collectors:
            vocabulary = zope.schema.vocabulary.SimpleVocabulary(
                [zope.schema.vocabulary.SimpleTerm(
                    value=collector,
                    token='/'.join(collector.getPhysicalPath()),
                    title=collector.title)
                 for collector in optional_collectors])

            name = 'selected_collectors'
            fields.append(
                (name,
                 zope.schema.Set(
                     __name__=name,
                     title=_(u"Sections"),
                     value_type=zope.schema.Choice(vocabulary=vocabulary))
                 ))
            interface.directlyProvides(fields[0][1],
                    collective.singing.interfaces.IDynamicVocabularyCollection)

        return zope.interface.interface.InterfaceClass(
            'Schema', bases=(collective.singing.interfaces.ICollectorSchema,),
            attrs=dict(fields))

    def add_topic(self):
        name = self.get_next_id()
        title = self.translate(_(u'Collection for ${title}', mapping={'title': self.title}))
        Products.CMFPlone.utils._createObjectByType(
            'Topic', self, id=name, title=title)
        self[name].unmarkCreationFlag()
        return self[name]

@component.adapter(Collector, zope.app.container.interfaces.IObjectAddedEvent)
def sfc_added(sfc, event):
    sfc.add_topic()

# These lists of factories are mutable: You can add to them:
collectors = [Collector, TextCollector, ReferenceCollector]
standalone_collectors = [Collector]

sort_criteria = dict(
     default=lambda cue: dict(query=cue, range='min'),
     effective=lambda cue: dict(query=(cue, DateTime.DateTime()), range='minmax'),
     )
