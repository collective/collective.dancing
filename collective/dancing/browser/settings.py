import z3c.form

from collective.dancing.browser.channel import ChannelAdministrationView
from collective.dancing.channel import INewslettersSettings
from collective.dancing.utils import switch_on
from collective.dancing import MessageFactory as _


class NewslettersSettingsForm(z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(INewslettersSettings)


class NewslettersSettingsView(ChannelAdministrationView):

    label = _(u'label_newsletters_settings_administration',
              default=u"Global settings")

    def contents(self):
        switch_on(self)
        return NewslettersSettingsForm(self.context, self.request)()
