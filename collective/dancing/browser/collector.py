import zope.publisher
from zope import schema
import zope.schema.vocabulary
from zope import component
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import field
from z3c.form import form, subform
import z3c.form.interfaces
import z3c.form.browser.select
import z3c.formwidget.query.widget
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import Products.CMFPlone.utils
from collective.singing.interfaces import ICollector
from plone.z3cform.crud import crud
from plone.app.z3cform import wysiwyg
import collective.singing.interfaces

from collective.dancing import MessageFactory as _
from collective.dancing import collector
from collective.dancing.browser import controlpanel
from collective.dancing.browser import query
from collective.dancing.utils import switch_on


class ManageCollectorsForm(crud.CrudForm):
    """Crud form for collectors.
    """
    update_schema = field.Fields(ICollector).select('title')
    view_schema = field.Fields(ICollector).select('title')

    @property
    def add_schema(self):
        return self.update_schema + field.Fields(
            schema.Choice(
            __name__='factory',
            title=_(u"Type"),
            vocabulary=zope.schema.vocabulary.SimpleVocabulary(
                [zope.schema.vocabulary.SimpleTerm(value=f, title=f.title)
                 for f in collector.standalone_collectors])
            ))

    def get_items(self):
        return [(ob.getId(), ob) for ob in self.context.objectValues()]

    def add(self, data):
        name = Products.CMFPlone.utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        self.context[name] = data['factory'](
            name, data['title'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field):
        if field == 'title':
            return item.absolute_url()

class CollectorAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    label = _(u"label_collector_administration",
              default=u'Collector administration')
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        switch_on(self)
        return ManageCollectorsForm(self.context, self.request)()

collector_fields = field.Fields(
    collective.singing.interfaces.ICollector).select('title', 'optional')

def heading(self):
    if self.label:
        return "<h%s>%s</h%s>" % (self.level, self.context.translate(self.label), self.level)

def prefix(self):
    return self.__class__.__name__ + '-'.join(self.context.getPhysicalPath())

class EditTopicForm(subform.EditSubForm):
    """Edit a single collector.
    """
    component.adapts(Products.ATContentTypes.content.topic.ATTopic,
                     None,
                     z3c.form.interfaces.IEditForm)
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')

    fields = field.Fields(
        schema.TextLine(__name__='title', title=_(u"Title")))

    @property
    def css_class(self):
        return "subform subform-level-%s" % self.level

    @property
    def label(self):
        return _(u"Collection: ${title}", mapping={'title': self.context.title})

    prefix = property(prefix)

    def contents_bottom(self):
        return u'<a href="%s/criterion_edit_form">%s</a>' % (
            self.context.absolute_url(), self.context.translate(_(u"Edit the Smart Folder")))

    heading = heading

class EditTextForm(subform.EditSubForm):
    component.adapts(collector.ITextCollector,
                     None,
                     z3c.form.interfaces.IEditForm)
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')

    fields = z3c.form.field.Fields(collector.ITextCollector).select(
        'title', 'value')
    fields['value'].widgetFactory[
        z3c.form.interfaces.INPUT_MODE] = wysiwyg.WysiwygFieldWidget

    @property
    def css_class(self):
        return "subform subform-level-%s" % self.level

    @property
    def label(self):
        return _(u"Rich text: ${title}", mapping={'title': self.context.title})

    prefix = property(prefix)

class EditReferenceForm(subform.EditSubForm):
    component.adapts(collector.IReferenceCollector,
                     None,
                     z3c.form.interfaces.IEditForm)
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')

    fields = z3c.form.field.Fields(
        collector.IReferenceCollector,
        query.IReferenceSelection).select('title', 'items')

    fields['items'].widgetFactory[
        z3c.form.interfaces.INPUT_MODE] = \
        z3c.formwidget.query.widget.QuerySourceFieldCheckboxWidget

    @property
    def css_class(self):
        return "subform subform-level-%s" % self.level

    @property
    def label(self):
        return _(u"Rich text: ${title}", mapping={'title': self.context.title})

    prefix = property(prefix)

class AddToCollectorForm(form.Form):
    ignoreContext = True
    ignoreRequest = True
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')
    css_class = "addform"

    prefix = property(prefix)
    heading = heading

    @property
    def label(self):
        return _(u"Add item to ${title}", mapping={'title': self.context.title})

    @property
    def fields(self):
        factory = schema.Choice(
            __name__='factory',
            title=_(u"Type"),
            vocabulary=zope.schema.vocabulary.SimpleVocabulary(
                [zope.schema.vocabulary.SimpleTerm(value=f, title=f.title)
                 for f in collector.collectors])
            )

        title = schema.TextLine(
            __name__='title',
            title=_(u"Title"))

        return z3c.form.field.Fields(factory, title)

    @z3c.form.button.buttonAndHandler(_('Add'), name='add')
    def handle_add(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = z3c.form.form.EditForm.formErrorsMessage
            return
        obj = data['factory'](self.context.get_next_id(), data['title'])
        self.context[obj.id] = obj
        self.status = _(u"Item added successfully.")

class DeleteFromCollectorForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')
    css_class = "deleteform"

    prefix = property(prefix)

    @z3c.form.button.buttonAndHandler(_('Remove block'), name='remove')
    def handle_remove(self, action):
        self.context.aq_parent.manage_delObjects([self.context.id])
        self.status = _("Item successfully deleted.")

class MoveBlockForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')
    css_class = "moveform"

    prefix = property(prefix)

    def _info_idx(self):
        infos = list(self.context.aq_parent._objects)
        info = None
        for info in infos:
            if info['id'] == self.context.id:
                break
        if info in infos:
            return infos.index(info)
        else:
            return 0

    def _move(self, delta):
        prev_index = self._info_idx()
        parent = self.context.aq_parent
        infos = list(parent._objects)
        my_info = infos[prev_index]
        del infos[prev_index]
        infos.insert(prev_index + delta, my_info)
        parent._objects = tuple(infos)

    @z3c.form.button.buttonAndHandler(
        _('Move block up'), name='up',
        condition=lambda form: form._info_idx() > 0)
    def handle_moveup(self, action):
        self._move(-1)
        self.status = _("Item successfully moved.")

    @z3c.form.button.buttonAndHandler(
        _('Move block down'), name='down',
        condition=lambda form: (form._info_idx() <
                                len(form.context.aq_parent._objects) - 1))
    def handle_movedown(self, action):
        self._move(1)
        self.status = _("Item successfully moved.")

class AbstractEditCollectorForm(object):
    level = 1

    @property
    def css_class(self):
        return "subform subform-level-%s" % self.level

    heading = heading

    def update(self):
        super(AbstractEditCollectorForm, self).update()
        addform = AddToCollectorForm(self.context, self.request)
        addform.level = self.level
        addform.update()

        actions = []
        for item in self.context.objectValues():
            acts = []
            for factory in DeleteFromCollectorForm, MoveBlockForm:
                form = factory(item, self.request)
                form.update()
                form.level = self.level + 1
                acts.append(form)
            actions.append(acts)

        editforms = []
        for item in self.context.objectValues():
             subform = component.getMultiAdapter(
                (item, self.request, self.parent_form),
                z3c.form.interfaces.ISubForm)
             subform.update()
             subform.level = self.level + 1
             editforms.append(subform)

        self.subforms = []
        for editform, acts in zip(editforms, actions):
            self.subforms.append(editform)
            self.subforms.extend(acts)
        self.subforms.append(addform)

class EditCollectorForm(AbstractEditCollectorForm, subform.EditSubForm):
    """Edit a single collector.
    """
    component.adapts(collective.singing.interfaces.ICollector,
                     zope.publisher.interfaces.http.IHTTPRequest,
                     z3c.form.interfaces.IEditForm)
    template = viewpagetemplatefile.ViewPageTemplateFile(
        'form-with-subforms.pt')
    fields = collector_fields

    prefix = property(prefix)

    @property
    def label(self):
        return _(u"Collector block: ${title}", mapping={'title': self.context.title})

    @property
    def parent_form(self):
        return self.parentForm

class EditRootCollectorForm(AbstractEditCollectorForm, form.EditForm):
    """Edit a single collector.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile(
        'form-with-subforms.pt')
    fields = collector_fields

    @property
    def parent_form(self):
        return self

class EditFilteredSubjectsCollectorForm(form.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    @property
    def fields(self):
        schema = self.context.full_schema
        field = schema[self.context.field_name]
        field.__name__ = 'filtered_items'
        field.interface = None
        return z3c.form.field.Fields(schema)

class CollectorEditView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Edit ${collector}',
                 mapping=dict(collector=self.context.title))

    def back_link(self):
        return dict(label=_(u"Up to Collector administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())

    def contents(self):
        switch_on(self)
        form = self.form(self.context, self.request)
        return '<div class="collector-form">' + form() + '</div>'

class RootCollectorEditView(CollectorEditView):
    form = EditRootCollectorForm

class FilteredCollectorEditView(CollectorEditView):
    form = EditFilteredSubjectsCollectorForm
