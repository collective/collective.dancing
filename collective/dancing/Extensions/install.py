from collective.singing.interfaces import ISalt
from collective.singing.async import IQueue

def beforeUninstall(portal, reinstall, product, cascade):
    """Don't remove our utilities on reinstall, thank you!"""
    if reinstall:
        return '', filter(lambda c: c not in ('utilities', 'adapters'), cascade)
    else:
        return '', cascade

def _remove_persistent_utils(portal):
    # http://plone.org/documentation/kb/manually-removing-local-persistent-utilities
    sm = portal.getSiteManager()

    util_obj = sm.getUtility(ISalt)
    sm.unregisterUtility(provided=ISalt)
    del util_obj
    sm.utilities.unsubscribe((), ISalt)
    try:
        del sm.utilities.__dict__['_provided'][ISalt]
    except KeyError:
        pass
    try:
        del sm.utilities._subscribers[0][ISalt]
    except KeyError:
        pass

    util = sm.queryUtility(IQueue, name='collective.dancing.jobs')
    sm.unregisterUtility(util, IQueue, name='collective.dancing.jobs')
    del util
    try:
        del sm.utilities._subscribers[0][IQueue]
    except KeyError:
        pass

def uninstall(portal, reinstall=False):
    if not reinstall:
        _remove_persistent_utils(portal)
