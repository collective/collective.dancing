import os
import tempfile

from zope.interface import Interface
import zc.lockfile
from Products.Five import BrowserView
from collective.singing.channel import channel_lookup

LOCKFILE_NAME = os.path.join(tempfile.gettempdir(),
                             __name__ + '.tick_and_dispatch')

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
        try:
            lock = zc.lockfile.LockFile(LOCKFILE_NAME)
        except zc.lockfile.LockError:
            return "`tick_and_dispatch` is locked by another process (%r)." % (
                LOCKFILE_NAME)

        try:
            return self._tick_and_dispatch()
        finally:
            lock.close()

    def _tick_and_dispatch(self):
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
