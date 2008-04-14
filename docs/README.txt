Singing and Dancing
===================

What is it?
-----------

*Singing and Dancing* is the next generation newsletter Product for
Plone.  It's an out of the box solution that works without
modification for most of your use cases.  And should you find
something that Singing and Dancing can't do, it's built to be easily
extended via plug-ins using the Zope 3 Component Architecture.

Singing and Dancing is still under heavy development.  We consider it
stable, but there are going to be API changes in the future.

Features
--------

Modern and extensible
  Singing and Dancing builds on the latest and greatest efforts in the
  Zope and Plone world.  It makes heavy use of the excellent
  ``z3c.form`` library and the Zope 3 Component Architecture.  This
  allows you to easily plug in and extend Singing and Dancing to fit
  your needs.

Well tested
  An extensive suite of automated tests make Singing and Dancing
  exceptionally stable and reliable.  We currently have 200+ tests.
  Singing and Dancing is not gonna leave you in the lurch!

Fully managable through the Plone interface
  Singing and Dancing is fully usable out the web.  An extensive set
  of forms reachable through the configuration panel let you as the
  user configure many details of your newsletters, like *when* they're
  sent (periodically or manually), *what* is sent (through the use of
  the *Smart Folder* interface, or manually), and to whom.

Subscriptions
  Singing and Dancing uses *confirmed subscription*, i.e. subscribers
  receive an e-mail to confirm their subscription.  Users can
  subscribe via a standard subscription form that lists all available
  newsletters in the site, or through individual subscription forms,
  e.g. in portlets.

Future
``````
A couple of features that we're going to implement in the near future:

Newsletter templates
  Take complete control over how the newsletters look that are sent
  out.  Create your own template or one of the templates that come
  pre-installed with the Singing and Dancing.  Manage newsletter
  templates in a pool for easy reuse.

Installation
------------

For deploying Singing and Dancing in production, you want to use a
buildout_.  A buildout for the development of Singing and Dancing
itself is available at:

  https://svn.plone.org/svn/collective/collective.dancing/trunk-buildout

This buildout includes the development versions of the
``collective.singing`` and ``collective.dancing`` packages.  For
production use, you can start by copying the buildout.cfg from this
development buildout, but modify it to not use development versions
but eggs from the CheeseShop.  To do this, remove this section::

  develop =
      src/collective.singing
      src/collective.dancing

Of course you can just add these two packages to your already existing
buildout or to your Repoze_ setup.  When using Buildout, make sure you
use the fakezope2eggs_ recipe to avoid downloading incompatible
versions of Zope 3 packages into your buildout.

If you find a bug, please `let us know`_.

Developers
----------

Singing & Dancing is built from scratch to be extensible.  All
components described in the `interfaces.py`_ file in
``collective.singing`` are pluggable.

Developer documentation exists in the form of doctests and Zope 3
interfaces in the source tree.  To check out the development buildout,
type this in your terminal::

  svn co http://svn.plone.org/svn/collective/collective.dancing/trunk-buildout singing-dancing-dev

When the checkout is complete, you can find the doctests in ``*.txt``
files in the ``src/collective.singing/collective/singing/`` and
``src/collective.dancing/collective/dancing/`` directories.  There's
also a documentation area for use cases and manuals in
``src/collective.dancing/docs/``.

Get in touch with us if you need help or have comments.  The `mailing
list`_ and the IRC channel ``#singing-dancing`` on Freenode_ are good
places for this.


.. _buildout: http://pypi.python.org/pypi/zc.buildout
.. _let us know: http://bugs.launchpad.net/singing-dancing/+filebug
.. _Repoze: http://repoze.org
.. _fakezope2eggs: http://danielnouri.org/blog/devel/zope/fakezope2eggs
.. _interfaces.py: http://dev.plone.org/collective/browser/collective.singing/trunk/collective/singing/interfaces.py
.. _mailing list: http://groups.google.com/group/singing-dancing
.. _Freenode: http://freenode.net