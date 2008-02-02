from zope import component
import Products.CMFPlone.interfaces

from Products.Five import BrowserView
from Products.Five.browser import pagetemplatefile

from collective.dancing import MessageFactory as _

def back_to_controlpanel(self):
    root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return dict(label=_(u"Up to newsletter control panel"),
                url=root.absolute_url() + '/newsletter-controlpanel.html')

class ControlPanelView(BrowserView):
    __call__ = pagetemplatefile.ViewPageTemplateFile('controlpanel.pt')
    contents = pagetemplatefile.ViewPageTemplateFile('controlpanel-links.pt')

    label = _(u"Newsletter configuration")

    def back_link(self):
        return dict(label=_(u"Up to Site Setup"),
                    url=self.context.absolute_url() + '/plone_control_panel')

