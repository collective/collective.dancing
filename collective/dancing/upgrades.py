import copy_reg
import persistent
import zc.queue
import logging

import collective.singing.channel
import collective.singing.subscribe
import collective.dancing.composer
from collective.singing.queue import CompositeQueue

logger = logging.getLogger('collective.dancing')
safe_reconstructor = copy_reg._reconstructor

def null_upgrade_step(tool):
    """ This is a null upgrade, use it when nothing happens """
    pass

def _reconstructor(cls, base, state):
    if issubclass(cls, collective.dancing.composer.HTMLComposer):
        obj = persistent.Persistent.__new__(cls, state)
        base.__init__(obj, state)
        return obj
    else:
        return safe_reconstructor(cls, base, state)

def fix_legacy_htmlcomposers(tool):
    """collective.dancing.composer.HTMLComposer used to derive from
    object.  We need to update all pickles of composers with this
    little brute force function.
    """
    site = tool.aq_parent
    copy_reg._reconstructor = _reconstructor
    try:
        if 'portal_newsletters' in site.objectIds():
            for channel in site['portal_newsletters'].channels.values():
                channel.composers = channel.composers
    finally:
        copy_reg._reconstructor = _reconstructor

def upgrade_to_compositequeue(tool):
    """collective.singing.message.MessageQueues used to store messages
    in zc.queue.Queue objects, which are inefficient for large queues.
    This upgrade modifies existing instances of MessageQueues to use
    zc.queue.CompositeQueue instead."""
    for channel in collective.singing.channel.channel_lookup():
        for key in channel.queue.keys():
            new = zc.queue.CompositeQueue()
            for item in channel.queue[key]:
                new.put(item)
            channel.queue[key] = new

def reindex_subscriptions(tool):
    """The fulltext index for subscriptions wasn't populated before
    version 0.7.2.  This upgrade step will reindex all subscriptions
    that it can find.
    """
    for channel in collective.singing.channel.channel_lookup():
        for sub in channel.subscriptions.values():
            collective.singing.subscribe._catalog_subscription(sub)

def upgrade_to_singing_compositequeue(tool):
    """collective.singing.message.MessageQueues used to store messages
    in zc.queue.CompositeQueue objects, which are inefficient when counting
    items in a large queue, because it needs to access many persistent sub-
    queues.
    This upgrade modifies existing instances of MessageQueues to use
    collective.singing.message.CompositeQueue instead."""
    for channel in collective.singing.channel.channel_lookup():
        logger.info("Updating queues in %s to singing CompositeQueue" % channel.name)
        for key in channel.queue.keys():
            if isinstance(channel.queue[key], CompositeQueue):
                continue
            new = CompositeQueue()
            for item in channel.queue[key]:
                new.put(item)
            channel.queue[key] = new
        logger.info("Updated queues in %s to singing CompositeQueue" % channel.name)

def upgrade_scheduled_sends(tool):
    """ Upgrade already scheduled items in Timed Schedulers
    to reflect code changes in 0.8.9.
    I.e. scheduler.items is now a list of (when, content, override_vars)
    instead of the previous (when, content)"""
    for channel in collective.singing.channel.channel_lookup():
        if isinstance(channel.scheduler,
                      collective.singing.scheduler.TimedScheduler):
            items = persistent.list.PersistentList()
            for item in channel.scheduler.items:
                try:
                    when, content = item
                    items.append((when, content, {}))
                    logger.info('Upgrading scheduled item "%s" for mailing-list "%s"' \
                                % (item, channel.Title()))
                except ValueError:
                    items.append(item)
            channel.scheduler.items = items
