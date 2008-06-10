from zope import interface
from zope import schema

from collective.dancing import MessageFactory as _

class ISendAndPreviewForm(interface.Interface):
    channels = schema.Set(
        title=_(u"The channel to send this through"),
        value_type=schema.Choice(
        vocabulary='collective.singing.vocabularies.ChannelVocabulary')
        )
    
    include_collector_items = schema.Bool(
        title=_(u"Include collector items"),
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
        required=False,
        )
