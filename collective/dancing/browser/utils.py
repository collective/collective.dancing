import os
import tempfile

from zope.interface import Interface
import zc.lockfile
from Products.Five import BrowserView
from collective.singing.channel import channel_lookup
from collective.dancing import utils

LOCKFILE_NAME = os.path.join(tempfile.gettempdir(),
                             __name__ + '.tick_and_dispatch')

class IDancingUtilsView(Interface):

    def tick_and_dispatch(self):
        """Tick all schedulers of all channels.  Then dispatch their
        queues.

        This is what you call from cron or zope clock server to get
        periodic sending.
        """

    def handle_bounce(self):
        """Process a list of bouncing e-mail addresses.

        Expects a list of e-mail addresses in the ``addrs`` request
        variable.
        """

class DancingUtilsView(BrowserView):

    bounce_limit = 2

    def tick_and_dispatch(self):
        """ """
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

        queue = utils.get_queue()
        num = queue.process()
        if num:
            for job in queue.finished[-num:]:
                msg += job.value + '\n'

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

    def handle_bounce(self):
        """ """
        count = 0
        addrs = self.request['addrs']
        if isinstance(addrs, (str, unicode)):
            addrs = [addrs]
        for channel in channel_lookup(only_subscribeable=True):
            for addr in addrs:
                subscriptions = channel.subscriptions.query(key=addr)
                for sub in subscriptions:
                    md = sub.metadata
                    bounces = md.get('bounces', 0)
                    if bounces >= self.bounce_limit:
                        md['pending'] = True
                        bounces = 0
                        count += 1
                    else:
                        bounces += 1
                    md['bounces'] = bounces
        return "%d addresses received, %d deactivated" % (len(addrs), count)

    def empty_queue(self):
        """ """
        queue = utils.get_queue()
        while True:
            try:
                queue.pull()
            except IndexError:
                pass # done
