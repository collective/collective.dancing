import collective.singing.interfaces

class IFullFormatter(collective.singing.interfaces.IFormatItem):
    """Format the item for use as main newsletter content.

    This is used when newsletters are created from an existing content
    object on the site.

    The formatter should only return the actual content markup, not a
    complete HTML document.
    """
