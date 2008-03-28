from zope import component
from zope import interface
from zope import schema
import zope.interface.interface
import zope.schema.vocabulary
import zope.schema.interfaces
import zope.app.container.interfaces
import zope.i18nmessageid
import DateTime
import OFS.Folder
import Products.CMFCore.utils
import Products.CMFPlone.interfaces
import Products.CMFPlone.utils
import Products.ATContentTypes.criteria.selection
import Products.ATContentTypes.criteria.path
import collective.singing.interfaces

from collective.dancing import utils
from collective.dancing import MessageFactory as _

class IATCriterionMediator(interface.Interface):
    field = schema.Object(
        title=u'Restrict',
        description=u'Field for restriction of criterion',
        schema=zope.schema.interfaces.IField,
        )

    def query_args(value):
        """Return a dict containing the query parameters that
        correspond to ``value``.
        """

class IATSelectionCriterion(interface.Interface):
    pass
interface.classImplements(
    Products.ATContentTypes.criteria.selection.ATSelectionCriterion,
    IATSelectionCriterion)

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

def criterions_vocabulary(context):
    terms = []
    for cr in context.topic.listCriteria():
        try:
            IATCriterionMediator(cr)
        except TypeError, e:
            continue
        else:
            terms.append(
                zope.schema.vocabulary.SimpleTerm(
                    value=cr.Field(),
                    title=cr.shortDesc,
                ))
    return zope.schema.vocabulary.SimpleVocabulary(terms)
interface.alsoProvides(criterions_vocabulary,
                       zope.schema.interfaces.IVocabularyFactory)

class CollectorContainer(OFS.Folder.Folder):
    Title = u"Collectors"

@component.adapter(CollectorContainer,
                   zope.app.container.interfaces.IObjectAddedEvent)
def container_added(container, event):
    name = 'default-latest-news'
    container[name] = SmartFolderCollector(
        name, u"Latest news")
    topic = container[name]['topic']
    type_crit = topic.addCriterion('Type', 'ATPortalTypeCriterion')
    type_crit.setValue('News Item')
    sort_crit = topic.addCriterion('created', 'ATSortCriterion')
    state_crit = topic.addCriterion('review_state',
                                    'ATSimpleStringCriterion')
    state_crit.setValue('published')
    topic.setSortCriterion('created', True)
    topic.setLayout('folder_summary_view')

class ICollectorSchema(interface.Interface):
    pass

@component.adapter(collective.singing.interfaces.ISubscription)
@interface.implementer(ICollectorSchema)
def collectordata_from_subscription(subscription):
    composer_data = collective.singing.interfaces.ICollectorData(subscription)
    return utils.AttributeToDictProxy(composer_data)

class SmartFolderCollector(OFS.Folder.Folder):
    interface.implements(collective.singing.interfaces.ICollector)
    
    def __init__(self, id, title):
        self.id = id
        self.title = self.Title = title
        self.user_restrictable_criterions = []
        super(SmartFolderCollector, self).__init__()

    def get_items(self, cue=None, subscription=None):
        topic = self['topic']
        query_args = {}

        if cue is not None and topic.hasSortCriterion():
            sort_criterion = topic.getSortCriterion()
            query_args[str(sort_criterion.field)] = dict(
                query=cue, range='min')

        if subscription is not None:
            sdata = collective.singing.interfaces.ICollectorData(subscription)
            for cvalue in sdata.values():
                mediator = None
                if hasattr(cvalue, '__iter__'):
                    if len(cvalue):
                        mediator = tuple(cvalue)[0].mediator
                        value = [cvalue.value for cvalue in cvalue]
                    else:
                        continue
                else:
                    mediator = cvalue.mediator
                    value = cvalue.value

                query_args.update(mediator.query_args(value))

        items = topic.queryCatalog(full_objects=True, **query_args)
        return items, DateTime.DateTime()

    @property
    def schema(self):
        # Joy: we need to wrap the topic ourselves into the Plone
        # root, because we're in a property, and properties lose
        # acquisition. :-/
        root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        self = self.__of__(root)
        topic = self['topic']

        # We collect our topic's criteria based on their "field",
        # which is a string that corresponds to a catalog index.
        criterions_by_fieldname = {}
        for cr in topic.listCriteria():
            criterions_by_fieldname[str(cr.Field())] = cr

        fields = []
        for name in self.user_restrictable_criterions:
            cr = criterions_by_fieldname.get(name)
            if cr is None:
                raise ValueError("Criterion %r not available." % name)
            try:
                mediator = IATCriterionMediator(cr)
            except TypeError, e:
                raise TypeError("No mediator adapter found for %r." % cr)
            else:
                field = mediator.field
                fields.append((name, field))

        return zope.interface.interface.InterfaceClass(
            'Schema', bases=(ICollectorSchema,), attrs=dict(fields))

    def added(self):
        Products.CMFPlone.utils._createObjectByType(
            'Topic', self, id='topic', title=self.title)
        self['topic'].unmarkCreationFlag()

        workflow = Products.CMFCore.utils.getToolByName(self, 'portal_workflow')
        workflow.doActionFor(self['topic'], 'publish')

@component.adapter(SmartFolderCollector,
                   zope.app.container.interfaces.IObjectAddedEvent)
def sfc_added(sfc, event):
    sfc.added()

class CriterionValue(object):
    def __init__(self, value, mediator):
        self.value = value
        self.mediator = mediator

    def __repr__(self):
        return "<CriterionValue with value %r, mediated by %r>" % (
            self.value, self.mediator)

    def __eq__(self, other):
        return (isinstance(other, CriterionValue) and
                other.value == self.value and
                other.mediator.criterion == self.mediator.criterion)

def _choice_field(criterion, vocabulary):
    return schema.Set(
        __name__=criterion.Field(),
        title=zope.i18nmessageid.Message(
            unicode(criterion.shortDesc), domain='collective.dancing'),
        value_type=schema.Choice(vocabulary=vocabulary))

class SelectionCriterionMediator(object):
    component.adapts(IATSelectionCriterion)
    interface.implements(IATCriterionMediator)

    def __init__(self, criterion):
        self.criterion = criterion

    @property
    def field(self):
        dl = self.criterion.getCurrentValues()
        values = self.criterion.Value()
        vocabulary = utils.LaxVocabulary.fromItems(
            [(v, CriterionValue(dl.getValue(v), self)) for v in values])
        return _choice_field(self.criterion, vocabulary)

    def query_args(self, value):
        return {self.criterion.Field(): value}

class PathCriterionMediator(object):
    component.adapts(Products.ATContentTypes.criteria.path.ATPathCriterion)
    interface.implements(IATCriterionMediator)

    def __init__(self, criterion):
        self.criterion = criterion

    @property
    def field(self):
        terms = []
        for folder in self.criterion.Value():
            path = '/'.join(folder.getPhysicalPath())
            term = zope.schema.vocabulary.SimpleTerm(
                value=CriterionValue(path, self),
                token=path,
                title=unicode(folder.Title(), 'UTF-8'))
            terms.append(term)

        vocabulary = utils.LaxVocabulary(terms)
        return _choice_field(self.criterion, vocabulary)

    def query_args(self, value):
        depth = self.criterion.Recurse() and -1 or 1
        return {self.criterion.Field(): dict(query=value, depth=depth)}
