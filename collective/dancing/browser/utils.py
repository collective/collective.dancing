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
        for channel in channel_lookup():
            if channel.scheduler is not None:
                channel.scheduler.tick(channel)
            if channel.queue is not None:
                channel.queue.dispatch()
           
    
