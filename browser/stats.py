from Products.Five import BrowserView
from Products.Five.browser import pagetemplatefile
from Products.statusmessages.interfaces import IStatusMessage

import collective.dancing.stats

class StatsView(BrowserView):
    template = pagetemplatefile.ViewPageTemplateFile('stats.pt')

    def __call__(self):
        if 'submitted' in self.request.form:
            self._clear()
        return self.template()

    def _clear(self):
        collective.dancing.stats.clear()
        IStatusMessage(self.request).addStatusMessage(
            "Statistics cleared", type='info')

    def statistics(self):
        return collective.dancing.stats.get_queued_stats()
