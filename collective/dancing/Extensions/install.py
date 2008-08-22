def beforeUninstall(portal, reinstall, product, cascade):
    """Don't remove our utilities on reinstall, thank you!"""
    if reinstall:
        return '', filter(lambda c: c not in ('utilities', 'adapters'), cascade)
    else:
        return '', cascade
