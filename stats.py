import datetime

import persistent.list
from zope import component
from zope.annotation.interfaces import IAnnotations

import Products.CMFPlone.interfaces

QUEUED_STATS = 'collective.dancing.queued_stats'

class Stat(object):
    def __init__(self, timestamp, channel_title, number_of_msgs):
        self.timestamp = timestamp
        self.channel_title = channel_title
        self.number_of_msgs = number_of_msgs

def get_queued_stats():
    site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    return IAnnotations(site).setdefault(
        QUEUED_STATS, persistent.list.PersistentList())

def clear_queued_stats():
    site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
    IAnnotations(site)[QUEUED_STATS] = persistent.list.PersistentList()

def message_queued(event):
    stats = get_queued_stats()
    stats.append(Stat(datetime.datetime.now(),
                      event.channel.title,
                      len(event.messages)))
