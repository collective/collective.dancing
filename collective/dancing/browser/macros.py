import zope.publisher.browser
from zope.app.pagetemplate import viewpagetemplatefile

class Macros(zope.publisher.browser.BrowserView):
    template = viewpagetemplatefile.ViewPageTemplateFile('macros.pt')
    
    def __getitem__(self, key):
        return self.template.macros[key]
