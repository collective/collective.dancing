from zope import interface
from zope import schema

from collective.dancing import MessageFactory as _

import datetime


class ISendAndPreviewForm(interface.Interface):
    channel = schema.Choice(
        title=_(u"The mailing-list to send this through"),
        vocabulary='collective.singing.vocabularies.SendableChannelVocabulary',
    )

    channel_and_collector = schema.Choice(
        title=_(u"The mailing-list/section to send this to"),
        description=_(
            u"Pick a channel to send to the whole list. "
            u"Pick a 'channel - section' to send this "
            u"is a segment of the mailing-list based on the optional "
            u"section they subscribered to. "
            u"Must have a Timed scheduler to work"),
        vocabulary='collective.dancing.sendnewsletter.ChannelAndCollectorVocab'
    )

    include_collector_items = schema.Bool(
        title=_(u"Include collector items"),
        description=_(u"Append automatically collected content in this "
                      "send-out"),
        default=True,
    )

    address = schema.TextLine(
        title=_(u"Address to send the preview to"),
        description=_(
            u"This is only required if you click 'Send preview' below"),
        required=False,
    )

    datetime = schema.Datetime(
        title=_(u"Scheduled time"),
        description=_(u"This is only required if you click "
                      "'Schedule distribution' below"),
        default=datetime.datetime.now(),
        required=False,
    )
