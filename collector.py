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
import Products.CMFPlone.interfaces
import Products.CMFPlone.utils
import Products.ATContentTypes.criteria.selection
import collective.singing.interfaces

class IATCriterionMediator(interface.Interface):
    field = schema.Object(
        title=u'Restrict',
        description=u'Field for restriction of criterion',
        schema=zope.schema.interfaces.IField,
        )

class IATSelectionCriterion(interface.Interface):
    pass
interface.classImplements(
    Products.ATContentTypes.criteria.selection.ATSelectionCriterion,
    IATSelectionCriterion)

def collector_vocabulary(context):
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    collectors = root['portal_newsletters']['collectors'].objectValues()
    return zope.schema.vocabulary.SimpleVocabulary.fromItems(
        [('/'.join(collector.getPhysicalPath()), collector)
         for collector in collectors])
interface.alsoProvides(collector_vocabulary,
                       zope.schema.interfaces.IVocabularyFactory)

class CollectorContainer(OFS.Folder.Folder):
    pass

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

class SmartFolderCollector(OFS.Folder.Folder):
    def __init__(self, id, title):
        self.id = id
        self.title = title
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
            for key, value in sdata.items():
                query_args[str(key)] = value

        items = topic.queryCatalog(full_objects=True, **query_args)
        return items, DateTime.DateTime() + 0.005

    @property
    def schema(self):
        # Joy: we need to wrap the topic ourselves into the Plone
        # root, because we're in a property, and properties lose
        # acquisition. :-/
        root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        self = self.__of__(root)
        topic = self['topic']
        
        criterions_by_fieldname = {}
        for cr in topic.listCriteria():
            criterions_by_fieldname[str(cr.field)] = cr

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
            'Schema', attrs=dict(fields))

    def added(self):
        Products.CMFPlone.utils._createObjectByType(
            'Topic', self, id='topic', title=self.title)
        self['topic'].unmarkCreationFlag()

@component.adapter(SmartFolderCollector,
                   zope.app.container.interfaces.IObjectAddedEvent)
def sfc_added(sfc, event):
    sfc.added()

class SelectionCriterionMediator(object):
    component.adapts(IATSelectionCriterion)
    interface.implements(IATCriterionMediator)

    def __init__(self, criterion):
        self.criterion = criterion

    @property
    def field(self):
        dl = self.criterion.getCurrentValues()
        values = self.criterion.Value()
        vocabulary = zope.schema.vocabulary.SimpleVocabulary.fromItems(
            [(v, dl.getValue(v)) for v in values])
        return schema.Choice(
            __name__=self.criterion.field,
            title=zope.i18nmessageid.Message(
                unicode(self.criterion.shortDesc), domain='collective.dancing'),
            vocabulary=vocabulary)
