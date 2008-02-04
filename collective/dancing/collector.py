from zope import component
from zope import interface
import zope.schema.vocabulary
import zope.schema.interfaces
import zope.app.container.interfaces
import DateTime
import OFS.Folder
import Products.CMFPlone.interfaces
import Products.CMFPlone.utils

def collector_vocabulary(context):
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return zope.schema.vocabulary.SimpleVocabulary.fromItems(
        [('/'.join(collector.getPhysicalPath()), collector) for collector in
         root['portal_newsletters']['collectors'].objectValues()])
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
    #sort_crit = topic.addCriterion('created', 'ATSortCriterion')
    state_crit = topic.addCriterion('review_state',
                                    'ATSimpleStringCriterion')
    state_crit.setValue('published')
    topic.setSortCriterion('created', True)
    topic.setLayout('folder_summary_view')

class SmartFolderCollector(OFS.Folder.Folder):
    def __init__(self, id, title):
        self.id = id
        self.title = title
        super(SmartFolderCollector, self).__init__()

    def get_items(self, cue=None, subscription=None):
        topic = self['topic']

        query_args = {}
        if cue is not None and topic.hasSortCriterion():
            sort_criterion = topic.getSortCriterion()
            query_args[str(sort_criterion.field)] = dict(
                query=cue, range='min')

        items = topic.queryCatalog(full_objects=True, **query_args)
        return items, DateTime.DateTime() + 0.0005

    schema = interface.Interface

    def added(self):
        Products.CMFPlone.utils._createObjectByType(
            'Topic', self, id='topic', title=self.title)
        self['topic'].unmarkCreationFlag()

@component.adapter(SmartFolderCollector,
                   zope.app.container.interfaces.IObjectAddedEvent)
def sfc_added(sfc, event):
    sfc.added()
