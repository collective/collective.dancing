from zope import component

from Products.Five.browser import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile 

from collective.dancing.interfaces import IFullFormatter

class PreviewNewsletterView(BrowserView):
    template = ViewPageTemplateFile("preview.pt")
    
    def __call__(self):
        view = component.getMultiAdapter(
            (self.context, self.request), IFullFormatter, name='html')

        return self.template(content=view(), title=self.context.title_or_id())
