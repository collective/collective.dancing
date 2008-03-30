import zope.publisher
from zope import schema
from zope import component
from zope import interface
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import field
from z3c.form import form, subform
import z3c.form.interfaces
import z3c.form.browser.select
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import Products.CMFPlone.utils
from collective.singing.interfaces import ICollector
from collective.singing.browser import crud
import collective.singing.interfaces
import collective.singing.z2

import OFS.interfaces

from collective.dancing import MessageFactory as _
from collective.dancing import collector
from collective.dancing.browser import controlpanel

class ManageCollectorsForm(crud.CrudForm):
    """Crud form for collectors.
    """
    update_schema = field.Fields(ICollector).select('title')
    view_schema = field.Fields(ICollector).select('title')

    def get_items(self):
        return [(ob.getId(), ob) for ob in self.context.objectValues()]

    def add(self, data):
        name = Products.CMFPlone.utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        self.context[name] = collector.SmartFolderCollector(
            name, data['title'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field):
        if field == 'title':
            return item.absolute_url()

class CollectorAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    label = _(u'Collector administration')
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        collective.singing.z2.switch_on(self)
        return ManageCollectorsForm(self.context, self.request)()

collector_fields = field.Fields(
    collective.singing.interfaces.ICollector).select('title', 'optional')

class IURL(interface.Interface):
    """ Adds url  """
    url = schema.TextLine(title=_(u"Link"))

class URL(object):
    component.adapts(OFS.interfaces.ITraversable)
    
    def __init__(self, context):
        self.url = context.absolute_url()

    
class EditTopicForm(subform.EditSubForm):
    """Edit a single collector.
    """
    component.adapts(Products.ATContentTypes.content.topic.ATTopic,
                     None,
                     z3c.form.interfaces.IEditForm)
    
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    fields = field.Fields(
        schema.TextLine(__name__='title',
                        title=_(u"Title"),
                        ),
        IURL['url'],
        )
    

class EditCollectorForm(subform.EditSubForm):
    """Edit a single collector.
    """
    component.adapts(collective.singing.interfaces.ICollector,
                     zope.publisher.interfaces.http.IHTTPRequest,
                     z3c.form.interfaces.IEditForm)

    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    fields = collector_fields

    @property
    def parent_form(self):
        return self.parentForm

    def update(self):
        super(EditRootCollectorForm, self).update()
        self.subforms = []
        for item in self.context.objectValues():
             subform = component.getMultiAdapter(
                (item, self.request, self.parentForm),
                z3c.form.interfaces.ISubForm)
             subform.update()
             self.subforms.append(subform)

class EditRootCollectorForm(form.EditForm):
    """Edit a single collector.
    """

    fields = collector_fields

    @property
    def parent_form(self):
        return self

    def update(self):
        super(EditRootCollectorForm, self).update()
        self.subforms = []
        for item in self.context.objectValues():
            
             subform = component.getMultiAdapter(
                (item, self.request, self), z3c.form.interfaces.ISubForm)
             subform.update()
             self.subforms.append(subform)
    
class CollectorEditView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')
    contents_template = ViewPageTemplateFile('collector-edit-contents.pt')

    def label(self):
        return _(u'Edit ${collector}',
                 mapping=dict(collector=self.context.title))

    def back_link(self):
        return dict(label=_(u"Up to Collector administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())

    def contents(self):
        collective.singing.z2.switch_on(self)
        self.form = EditRootCollectorForm(self.context, self.request)
        return self.contents_template()
        
