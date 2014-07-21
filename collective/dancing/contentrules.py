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


from zope.site.hooks import getSite
from zope.i18n import translate

from Acquisition import aq_inner, aq_base


logger = logging.getLogger("collective.dancing")


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

    subject = u''
    source = u''
    recipients = u''
    message = u''

    element = 'collective.dancing.actions.Channel'

    @property
    def summary(self):
        return _(u"Email report to ${recipients}",
                 mapping=dict(recipients=self.recipients))


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

        channel = self.element.channel_and_collector[0]
        channel_paths = ['/'.join(channel.getPhysicalPath())]
        newsletter_path = "/".join(context.getPhysicalPath())
        newsletter_uid = IUUID(context)
        include_collector_items = self.element.include_collector_items
        override_vars = self.get_override_vars()

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

    collector = schema.Set(title=_(u"Content type"),
                              description=_(u"The content type to check for."),
                              required=True,
                              value_type=schema.Choice(vocabulary="plone.app.vocabularies.ReallyUserFriendlyTypes"))


class CollectorCondition(SimpleItem):
    """The actual persistent implementation of the collector condition element.

    Note that we must mix in SimpleItem to keep Zope 2 security happy.
    """
    implements(ICollectorCondition, IRuleElementData)

    check_types = []
    element = "collective.dancing.contentrules.Collector"

    @property
    def summary(self):
        portal = getSite()
        portal_types = getToolByName(portal, 'portal_types')
        titles = []
        for name in self.check_types:
            fti = getattr(portal_types, name, None)
            if fti is not None:
                title = translate(fti.Title(), context=portal.REQUEST)
                titles.append(title)
        return _(u"Content types are: ${names}", mapping=dict(names=", ".join(titles)))


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
        if not hasattr(aq_base(obj), 'getTypeInfo'):
            return False

        # get the collector. Run the collector and see if obj is in the results

        ti = obj.getTypeInfo() # getTypeInfo can be None
        if ti is None:
            return False
        return ti.getId() in self.element.check_types


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
