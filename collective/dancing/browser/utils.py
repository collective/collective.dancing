from zope.interface import Interface
from Products.Five import BrowserView
from collective.dancing.channel import channel_lookup

class IDancingUtilsView(Interface):
    
    def tick_and_dispatch(self):
        """ Tick all schedulers of all channels.
            Then dispatch their queues.
            
            This is what you call from cron or
            zope clock server to get periodic
            sending.
            """
    
class DancingUtilsView(BrowserView):

    def tick_and_dispatch(self): 
        """ Tick all schedulers of all channels.
            Then dispatch their queues. """
        msg = u''
        for channel in channel_lookup():
            if channel.scheduler is not None:
                queued = channel.scheduler.tick(channel)
            if channel.queue is not None:
                status = channel.queue.dispatch()
            msg += u'%s: %d messages queued, dispatched: %s\n' % (channel.name, queued or 0, str(status))    
        return msg
