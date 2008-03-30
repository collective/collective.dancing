from zope import component
import Products.CMFPlone.interfaces

from Products.Five import BrowserView
from Products.Five.browser import pagetemplatefile

from collective.singing import z2

from collective.dancing import MessageFactory as _
from collective.dancing.browser.channel import ManageChannelsForm

def back_to_controlpanel(self):
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return dict(label=_(u"Up to Singing & Dancing configuration"),
                url=root.absolute_url() + '/portal_newsletters')

class ControlPanelView(BrowserView):
    __call__ = pagetemplatefile.ViewPageTemplateFile('controlpanel.pt')
    contents = pagetemplatefile.ViewPageTemplateFile('controlpanel-links.pt')

    label = _(u"Singing & Dancing configuration")

    def back_link(self):
        return dict(label=_(u"Up to Site Setup"),
                    url=self.context.absolute_url() + '/plone_control_panel')
                    
    def channelcontents(self):
        # A call to 'switch_on' is required before we can render z3c.forms.
        #from collective.dancing.channel import ManageChannelsForm
        z2.switch_on(self)
        return ManageChannelsForm(self.context.channels, self.request)()

