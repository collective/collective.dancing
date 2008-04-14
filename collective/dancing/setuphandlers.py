import five.intid.site

def importVarious(context):
    """Import various settings.

    Provisional handler that does initialization that is not yet taken
    care of by other handlers.
    """
    # Only run step if a flag file is present
    if context.readDataFile('dancing_various.txt') is None:
        return
    site = context.getSite()
    five.intid.site.add_intids(site)
