import copy_reg
import persistent
import collective.dancing.composer

safe_reconstructor = copy_reg._reconstructor

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
