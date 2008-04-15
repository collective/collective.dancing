from zope import schema
from zope.app.pagetemplate import viewpagetemplatefile
from z3c.form import form
from z3c.form import field
from z3c.form import button
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
import collective.singing.z2

from collective.dancing import MessageFactory as _

class EditSchedulerForm(form.EditForm):
    """Edit a single collector.
    """
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    @property
    def fields(self):
        return field.Fields(collective.singing.interfaces.IScheduler).select(
            'triggered_last', 'active')

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handle_apply(self, action):
        return super(EditSchedulerForm, self).handleApply.func(self, action)

    @button.buttonAndHandler(_('Trigger now'), name='trigger')
    def handle_trigger(self, action):
        queued = self.context.trigger(self.context.aq_inner.aq_parent, self.request)
        if queued:
            self.status = _(u"${number} messages queued.",
                            mapping=dict(number=queued))
        else:
            self.status = _(u"No messages queued.")

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
        collective.singing.z2.switch_on(self)
        return EditSchedulerForm(self.context, self.request)()
