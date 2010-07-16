import z3c.form
from plone.z3cform import z2

from collective.dancing.browser.channel import ChannelAdministrationView
from collective.dancing.channel import INewslettersSettings
from collective.dancing import MessageFactory as _


class NewslettersSettingsForm(z3c.form.form.EditForm):
    fields = z3c.form.field.Fields(INewslettersSettings)


class NewslettersSettingsView(ChannelAdministrationView):

    label = _(u'label_newsletters_settings_administration',
              default=u"Global settings")

    def contents(self):
        # Calling 'switch_on' is required before we can render z3c.forms.
        z2.switch_on(self)
        return NewslettersSettingsForm(self.context, self.request)()
