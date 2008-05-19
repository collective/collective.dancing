from zope.interface import Interface
from Products.Five import BrowserView
from collective.singing.channel import channel_lookup

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
            queued = status = None
            if channel.scheduler is not None:
                queued = channel.scheduler.tick(channel, self.request)
            if channel.queue is not None:
                status = channel.queue.dispatch()
            d = {'channel':channel.name,
                 'queued':queued or 0,
                 'status':str(status or (0,0))}
            msg += u'%(channel)s: %(queued)d messages queued, dispatched: %(status)s\n' % d 
        return msg
