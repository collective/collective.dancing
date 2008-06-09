from zope.app.pagetemplate import viewpagetemplatefile
from zope import schema
from z3c.form import form
from z3c.form import field
from z3c.form import button
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from plone.z3cform import z2
import collective.singing.interfaces

from collective.dancing import MessageFactory as _

class EditPeriodicSchedulerForm(form.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    @property
    def fields(self):
        return field.Fields(collective.singing.interfaces.IScheduler).select(
            'triggered_last', 'active')

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handle_apply(self, action):
        return super(
            EditPeriodicSchedulerForm, self).handleApply.func(self, action)

    @button.buttonAndHandler(_('Trigger now'), name='trigger')
    def handle_trigger(self, action):
        queued = self.context.trigger(
            self.context.aq_inner.aq_parent, self.request)
        if queued:
            self.status = _(u"${number} messages queued.",
                            mapping=dict(number=queued))
        else:
            self.status = _(u"No messages queued.")

class EditTimedSchedulerEntryForm(form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')
    ignoreContext = True

    @property
    def fields(self):
        return field.Fields(
            schema.Bool(__name__='selected',
                        title=_(self.context[0])))

class EditTimedSchedulerForm(form.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile(
        'form-with-subforms.pt')

    @property
    def fields(self):
        return field.Fields(collective.singing.interfaces.IScheduler).select(
            'active')

    def update(self):
        self.subforms = []
        for entry in self.context.items:
            self.subforms.append(
                EditTimedSchedulerEntryForm(entry, self.request))

    @button.buttonAndHandler(_('Remove entries'), name='remove')
    def handle_remove(self, action):
        for subform in self.subforms:
            pass #XXX


class SchedulerEditView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    def label(self):
        return _(u'Edit ${selector} for ${channel}',
                 mapping=dict(selector=self.context.title,
                              channel=self.context.aq_inner.aq_parent.title))

    def back_link(self):
        return dict(
            label=_(u"Up to Channels administration"),
            url=self.context.aq_inner.aq_parent.aq_parent.absolute_url())

    def contents(self):
        z2.switch_on(self)
        return self.form(self.context.aq_inner, self.request)

class PeriodicSchedulerEditView(SchedulerEditView):
    form = EditPeriodicSchedulerForm

class TimedSchedulerEditView(SchedulerEditView):
    form = EditPeriodicSchedulerForm

