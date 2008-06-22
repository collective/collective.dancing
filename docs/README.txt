=================
Singing & Dancing
=================

.. contents::

What is it?
===========

*Singing & Dancing* is the next generation newsletter Product for
Plone.  It's an out of the box solution that works without
modification for most of your use cases.  And should you find
something that Singing & Dancing can't do, it's built to be easily
extended via plug-ins using the Zope 3 Component Architecture.

Features
========

Modern and extensible
  Singing & Dancing builds on the latest and greatest efforts in the
  Zope and Plone world.  It makes heavy use of the excellent
  ``z3c.form`` library and the Zope 3 Component Architecture.  This
  allows you to easily plug in and extend Singing & Dancing to fit
  your needs.

Well tested
  An extensive suite of automated tests make Singing & Dancing
  exceptionally stable and reliable.  We currently have 200+ tests.
  Singing & Dancing is not gonna leave you in the lurch!

Fully managable through the Plone interface
  Singing & Dancing is fully usable out of the box.  An extensive
  set of forms reachable through the configuration panel let you as
  the user configure many details of your newsletters, like *when*
  they're sent (periodically or manually), *what* is sent (through the
  use of the *Smart Folder* interface, or manually), and to whom.

Subscriptions
  Singing & Dancing uses *confirmed subscription*, i.e. subscribers
  receive an e-mail to confirm their subscription.  Users can
  subscribe via a standard subscription form that lists all available
  newsletters in the site, or through individual subscription forms,
  e.g. in portlets.

Future
------

A couple of features that we're going to implement in the near future:

Newsletter templates
  Take complete control over how the newsletters look that are sent
  out.  Create your own template or one of the templates that come
  pre-installed with the Singing & Dancing.  Manage newsletter
  templates in a pool for easy reuse.

.. image:: http://danielnouri.org/media/singing-dancing.jpg
   :alt: Singing & Dancing Logo by Giuseppe Zizza

Installation
============

Singing & Dancing is available as `Python eggs on PyPI`_.  To install,
you can simply depend_ on the ``collective.dancing`` package in your
own site policy package, and add fakezope2eggs_ to your buildout_
configuration, as explained below.

Alternatively, add ``collective.dancing`` to the list of eggs in your
``buildout.cfg`` if you don't have your own package.  This is what we
explain below.

Sadly, we don't support Repoze_ at this poiint.

Installing S&D with Buildout
----------------------------

If you don't know what buildout is or `how to create a buildout`_,
`follow this tutorial`_ first.

These instructions assume that you already have a Plone 3 buildout
that's built and ready to run.

1) Edit your buildout.cfg file and look for the ``eggs`` key in the
   ``instance`` section.  Add ``collective.dancing`` to that list.
   Your list will look something like this::

     eggs =
         ${buildout:eggs}
         ${plone:eggs}
         collective.dancing

   In the same section, look for the ``zcml`` key.  Add
   ``collective.dancing`` here, too::

     zcml = collective.dancing

2) Still in your buildout configuration file, look for the ``[zope2]``
   section (which uses the ``plone.recipe.zope2install`` recipe), and
   add the following lines to it::

     fake-zope-eggs = true
     additional-fake-eggs = ZODB3
     skip-fake-eggs =
         zope.testing
         zope.component
         zope.i18n

3) Now that we're done editing the buildout configuration file, we can
   run buildout again::

     $ ./bin/buildout -v

4) That's it!  You can now start up your Zope instance, and then
   install Singing & Dancing in your Plone site by visiting the
   *Add-on Products* site control panel.

   Should these instructions not work for you, `contact us`_.

It's installed.  What's next?
-----------------------------

You'll now have an entry in the control panel to *Singing & Dancing*.
This will lead you to to the advanced configuration panel of S&D.

Note that there's already a default newsletter set up for your
convenience.  You can create a *Channel subscribe portlet* to enable
your users to subscribe to this channel, or you can point them to
http://yoursite/portal_newsletters/channels/default-channel/subscribe.html

To send out a newsletter, go to any portal object, like the Plone
front page, and click *Actions -> Send as newsletter*.

The advanced configuration panel of S&D gives you many more ways to
send newsletters, like periodically and from automatically collected
content.

Processing the message queue
----------------------------

One important thing to note is that S&D usually queues messages in its
own message queue before sending them out.  You might have noticed
that when you send out a newsletter, S&D tells you that it queued the
messages.

In a production setup, you would normally process the message queue
periodically using the built-in Zope ClockServer_.  While you're
testing, you can visit the *Statistics* screen in the S&D advanced
configuration panel and manually flush the queues.  If your mail
configuration in Plone is set up correctly, you should be sending mail
out now.

To set up ClockServer to trigger the processing automatically for you,
add this stanza to the Zope 2 ``instance`` section of your buildout
configuration and rerun ``bin/buildout -v``::

  zope-conf-additional = 
      <clock-server>
        method /portal/@@dancing.utils/tick_and_dispatch
        period 300
        user admin
        password admin
        host localhost
      </clock-server>

This will process the message queue every five minutes.  It assumes
that your Plone site is called ``portal`` and that your username and
password are ``admin``.

**Note**: You must not set up this ClockServer on more than one
instance.  The processing makes sure it's not invoked twice at the
same time by using file locking.

Upgrade
=======

If you're upgrading your version of Singing & Dancing, it might be
that you need to run an upgrade of the database.  In the
``portal_setup`` tool in the ZMI, visit the *Upgrades* tab and run any
available new upgrades for the ``collective.dancing:default`` profile.


Contact us
==========

If you have a question, or comment, get in touch with us!  Our
`mailing list`_ is a good place to do so. If you find a bug, please
`let us know`_. We also have an IRC channel called
``#singing-dancing`` on Freenode_.

Developers
==========

Singing & Dancing is built from scratch to be extensible.  All
components described in the `interfaces.py`_ file in
``collective.singing`` are pluggable.

Developer documentation exists in the form of doctests and Zope 3
interfaces in the source tree.  To check out the development buildout,
type this into your terminal::

  svn co http://svn.plone.org/svn/collective/collective.dancing/trunk-buildout singing-dancing-dev

When the checkout is complete, you can find the doctests in ``*.txt``
files in the ``src/collective.singing/collective/singing/`` and
``src/collective.dancing/collective/dancing/`` directories.  There's
also a documentation area for use cases and manuals in
``src/collective.dancing/docs/``.

The latest version of collective.dancing itself can also be found in
the `Subversion repository`_.

Get in touch with us if you need help or have comments.  See the
`Contact us`_ section.


.. _Python eggs on PyPI: http://pypi.python.org/pypi/collective.dancing
.. _depend: http://peak.telecommunity.com/DevCenter/setuptools#declaring-dependencies
.. _fakezope2eggs: http://danielnouri.org/blog/devel/zope/fakezope2eggs
.. _buildout: http://pypi.python.org/pypi/zc.buildout
.. _Repoze: http://repoze.org
.. _how to create a buildout: http://plone.org/documentation/tutorial/buildout/creating-a-buildout-for-your-project
.. _follow this tutorial: http://plone.org/documentation/tutorial/buildout
.. _ClockServer: http://plope.com/software/ClockServer/
.. _let us know: http://bugs.launchpad.net/singing-dancing/+filebug
.. _mailing list: http://groups.google.com/group/singing-dancing
.. _Freenode: http://freenode.net
.. _interfaces.py: http://dev.plone.org/collective/browser/collective.singing/trunk/collective/singing/interfaces.py
.. _Subversion repository: http://svn.plone.org/svn/collective/collective.dancing/trunk#egg=collective.dancing-dev
