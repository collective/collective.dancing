from zope import component
import Products.CMFPlone.interfaces

from Products.Five import BrowserView
from Products.Five.browser import pagetemplatefile

from collective.dancing import MessageFactory as _
try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

def back_to_controlpanel(self):
    root = getSite()
    return dict(label=_(u"Up to Singing & Dancing configuration"),
                url=root.absolute_url() + '/portal_newsletters')

class ControlPanelView(BrowserView):
    __call__ = pagetemplatefile.ViewPageTemplateFile('controlpanel.pt')
    contents = pagetemplatefile.ViewPageTemplateFile('controlpanel-links.pt')

    label = _(u"Singing & Dancing configuration")

    def back_link(self):
        root = getSite()

        return dict(label=_(u"Up to Site Setup"),
                    url=root.absolute_url() + '/plone_control_panel')
