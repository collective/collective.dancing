from zope import interface
from zope import schema

import collective.singing.interfaces

from collective.dancing import MessageFactory as _

class IFullFormatter(interface.Interface):
    """Format the item for use as main newsletter content.

    This is used when newsletters are created from an existing content
    object on the site.

    The formatter should only return the actual content markup, not a
    complete HTML document.
    """

class IHTMLComposer(collective.singing.interfaces.IComposer,
                    collective.singing.interfaces.IComposerBasedSecret):
    """An HTML composer.
    """

    from_name = schema.TextLine(
        title=_(u"From name"),
        description=_(u"The sender name that will appear in messages sent from this mailing-list."),
        required=False,
        )
    from_address = schema.TextLine(
        title=_(u"From address"),
        description=_(u"The from address that will appear in messages sent from this composer."),
        required=False,
        )
    subject = schema.TextLine(
        title=_(u"Message subject"),
        description=_(u"You may use a number of variables here, like "
                      "${site_title}."),
        required=False,
        )
    replyto_address = schema.TextLine(
        title=_(u"Reply-to address"),
        description=_(u"The reply-to address that will appear in messages sent from this composer."),
        required=False,
        )
    header_text = schema.Text(
        title=_(u"Header text"),
        description=_(u"Text to appear at the beginning of every message. "
                      "You may use a number of variables here including "
                      "${subject}."),
        required=False,
        )
    footer_text = schema.Text(
        title=_(u"Footer text"),
        description=_(u"Text to appear at the end of every message"),
        required=False,
        )
    stylesheet = schema.Text(
        title=_(u"CSS Stylesheet"),
        description=_(u"The stylesheet will be applied to the document."),
        required=False,
        )
    template_name = schema.Choice(
        title=_(u"Template"),
        description=_(u"The template that will be used."),
        required=True,
        default='default',
        vocabulary='html_template_vocabulary',
        )

class IHTMLComposerTemplate(interface.Interface):
    """A marker interface to say that this template object can be used
    as a template for the HTMLComposer"""

