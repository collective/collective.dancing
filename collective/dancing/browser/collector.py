from zope import schema
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import field
from z3c.form import form
import z3c.form.interfaces
import z3c.form.browser.select
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import Products.CMFPlone.utils
from collective.singing.interfaces import ICollector
from collective.singing.browser import crud
import collective.singing.interfaces
import collective.singing.z2

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

    def link(self, item, field, value):
        if field == 'title':
            return item.absolute_url()

class CollectorAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    label = _(u'Newsletter Collectors administration')
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        collective.singing.z2.switch_on(self)
        return ManageCollectorsForm(self.context, self.request)()

class EditCollectorForm(form.EditForm):
    """Edit a single collector.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    @property
    def fields(self):
        fields = field.Fields(collective.singing.interfaces.ICollector).select(
            'title')

        criterions = schema.Set(
            __name__='user_restrictable_criterions',
            title=_(u"User restrictable criterions"),
            value_type=schema.Choice(vocabulary='User restrictable criterions'))
        fields += field.Fields(criterions)
        return fields

class CollectorEditView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')
    contents_template = ViewPageTemplateFile('collector-edit-contents.pt')

    def label(self):
        return _(u'Edit ${collector}',
                 mapping=dict(collector=self.context.title))

    def back_link(self):
        return dict(label=_(u"Up to Collectors administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())

    def contents(self):
        collective.singing.z2.switch_on(self)
        self.form = EditCollectorForm(self.context, self.request)
        return self.contents_template()
        
