import logging
import traceback
from smtplib import SMTPException

from plone.contentrules.rule.interfaces import IRuleElementData, IExecutable
from plone.stringinterp.interfaces import IStringInterpolator
from plone.uuid.interfaces import IUUID
from zope.component import adapts
from zope.component.interfaces import ComponentLookupError
from zope.formlib import form
from zope.interface import Interface, implements
from zope import schema

from Acquisition import aq_inner
from OFS.SimpleItem import SimpleItem
from Products.CMFCore.utils import getToolByName
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.MailHost.MailHost import MailHostError

from collective.dancing import MessageFactory as _
from plone.app.contentrules.browser.formhelper import AddForm, EditForm
from collective.dancing.browser.sendnewsletter import _assemble_messages
import collective.singing
from collective.dancing import utils


from zope.site.hooks import getSite
from zope.i18n import translate

from Acquisition import aq_inner, aq_base


logger = logging.getLogger("collective.dancing")



# A content rules based scheduler
# content rule action to send as a newsletter - lets you pick channel to send to, and date to use to schedule
# a content rule filter to use a collector to determine (or could use collective.keywordcondition 1.0b1)
# can just use timed schedular.
# some how also need to pick a section to send to? or might have to include collector. Except that would be confusing
# as email will go to everyone regardless.

# e.g
# 1. object published
# 2. triggers rule
# 3. item is in collector results
# 4. effective date used to schedule
# 5. use send as newsletter, schedule and don't include collector results



# or
# every minute schedular
# modify collectors to pick a que field (instead of modified it might be start or effective
# also don't store the queue unless an item actually matched. This will help by reducing transactions.
# this will have the side effect that if an event moves its date into the past it can get triggered.
# it also means it runs all teh searches on every trigger for every subscriber, which isn't very efficient






class IChannelAction(Interface):
    """Definition of the configuration available for a send to channel action
    """
    channel_and_collector = schema.Choice(
        title=_("Select channel to send item to. Optionally also select the specific section"),
        vocabulary='collective.dancing.sendnewsletter.ChannelAndCollectorVocab'
        )
#    schedule_field = schema.TextLine(title=_(u"Schedule Field"),
#                              description=_(u"Pick which field to use to determine when the newsletter is sent"),
#                              required=True)


class ChannelAction(SimpleItem):
    """
    The implementation of the action defined before
    """
    implements(IChannelAction, IRuleElementData)

    channel_and_collector = u''

    element = 'collective.dancing.actions.Channel'

    @property
    def summary(self):
        channel, collector = self.channel_and_collector
        try:
            title = channel + " - " + collector
        except:
            title = channel
        return _(u"Send to channel ${channel}",
                 mapping=dict(channel=title))


class ChannelActionExecutor(object):
    """The executor for this action.
    """
    implements(IExecutable)
    adapts(Interface, IChannelAction, Interface)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):

        context = self.event.object

        channel_path, section_title = self.element.channel_and_collector
        channel_paths = [channel_path]
        newsletter_path = "/".join(context.getPhysicalPath())
        try:
            newsletter_uid = IUUID(context)
        except TypeError:
            # we got a could not adapt error. Object which can't send.
            return False
        #include_collector_items = self.element.include_collector_items
        include_collector_items = False
        override_vars = {} # later could support saving overrides
        site = getSite()
        channel = site.unrestrictedTraverse(channel_path)
        if section_title is not None:
            for section in channel.collector.get_optional_collectors():
                if section.title == section_title:
                    override_vars["subscriptions_for_collector"] = section
                    break

        job = collective.singing.async.Job(_assemble_messages,
                                            channel_paths,
                                            newsletter_uid,
                                            newsletter_path,
                                            include_collector_items,
                                            override_vars)
        title = _(u"Send '${context}' through ${channel}.",
                  mapping=dict(
            context=context.Title().decode(context.plone_utils.getSiteEncoding()),
            channel=u'"%s"' % channel.title))
        job.title = title
        utils.get_queue().pending.append(job)

        logger.info(u"Messages queued for delivery.")
        return True


class ChannelAddForm(AddForm):
    """
    An add form for the mail action
    """
    form_fields = form.FormFields(IChannelAction)
    label = _(u"Add Channel Action")
    description = _(u"A channel action can send item as a newsletter")
    form_name = _(u"Configure element")

    # custom template will allow us to add help text
#    template = ViewPageTemplateFile('templates/mail.pt')

    def create(self, data):
        a = ChannelAction()
        form.applyChanges(a, self.form_fields, data)
        return a


class ChannelEditForm(EditForm):
    """
    An edit form for the mail action
    """
    form_fields = form.FormFields(IChannelAction)
    label = _(u"Edit Channel Action")
    description = _(u"A channel action can send an item as a newsletter")
    form_name = _(u"Configure element")

    # custom template will allow us to add help text
#    template = ViewPageTemplateFile('templates/mail.pt')


####
# Collector ContentRules condition
####


class ICollectorCondition(Interface):
    """Interface for the configurable aspects of a collector condition.

    This is also used to create add and edit forms, below.
    """

    channel_and_collector = schema.Choice(
        title=_("Select collector to filter item by. Optionally also select the specific section"),
        vocabulary='collective.dancing.sendnewsletter.ChannelAndCollectorVocab')


class CollectorCondition(SimpleItem):
    """The actual persistent implementation of the collector condition element.

    Note that we must mix in SimpleItem to keep Zope 2 security happy.
    """
    implements(ICollectorCondition, IRuleElementData)

    channel_and_collector = (None,None)
    element = "collective.dancing.contentrules.Collector"

    @property
    def summary(self):
        channel, collector = self.channel_and_collector
        try:
            title = channel + " - " + collector
        except:
            title = channel
        return _(u"Filter by collector ${channel}",
                 mapping=dict(channel=title))

class FakeSubscriber:
    collector_data = {}


class CollectorConditionExecutor(object):
    """The executor for this condition.

    This is registered as an adapter in configure.zcml
    """
    implements(IExecutable)
    adapts(Interface, ICollectorCondition, Interface)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        obj = aq_inner(self.event.object)

        # get the collector. Run the collector and see if obj is in the results
        use_cue = None
        subscription = None
        path, collector_title = self.element.channel_and_collector
        site = getSite()
        channel = site.unrestrictedTraverse(path)
        collector = channel.collector
        items = []

        #HACK: reindex seems to fire after contentrules so you can't use catalog queries on data that's could have changed
        # for example rule for state change and rely on collector that only finds published items
        # for now we will do a reindex now. This will likely cause a double reindex which isn't nice
        obj.reindexObject()

        subscription = FakeSubscriber()
        if collector_title is None:
            # use selected collector on the channel
            # warning, this means that everyone on the channel will get anything that one part of the collector matched.
            subscription.collector_data['selected_collectors'] = set([collector])
            items, cue = collector.get_items(use_cue, subscription)
        else:
            for section in channel.collector.get_optional_collectors():
                if section.title == collector_title:
                    # we are faking the subscriber as items are only returned for optional collectors if subscribed to
                    subscription.collector_data['selected_collectors'] = set([section])
                    items, cue = section.get_items(use_cue, subscription)

        return obj in items


class CollectorAddForm(AddForm):
    """An add form for Collector conditions.
    """
    form_fields = form.FormFields(ICollectorCondition)
    label = _(u"Add Content Type Condition")
    description = _(u"A collector condition makes the rule apply items that match the collector.")
    form_name = _(u"Configure element")

    def create(self, data):
        c = CollectorCondition()
        form.applyChanges(c, self.form_fields, data)
        return c


class CollectorEditForm(EditForm):
    """An edit form for Collector conditions
    """
    form_fields = form.FormFields(ICollectorCondition)
    label = _(u"Edit Content Type Condition")
    description = _(u"A collector condition makes the rule apply items that match the collector.")
    form_name = _(u"Configure element")
