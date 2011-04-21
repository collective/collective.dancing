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

.. image:: http://danielnouri.org/media/singing-dancing.jpg
   :alt: Singing & Dancing Logo by Giuseppe Zizza

User Manual
===========

The Singing & Dancing user manual is available here:
http://www.webtide.co.za/how-to/singing-dancing-user-manual

Installation
============

Installation of Singing & Dancing uses buildout_.  If you don't know
what buildout is or `how to create a buildout`_, `follow this
tutorial`_ first.

These instructions assume that you already have a Plone buildout that's built 
and ready to run.

Singing & Dancing is available as `Python eggs on PyPI`_.

To install Singing & Dancing, add it to your buildout by following
these steps:

* Plone 3.x

  1) Edit your ``buildout.cfg`` file and look for the ``[buildout]``
     section.  Add an ``extends =`` option in that section like the
     following::
    
         [buildout]
         extends = https://svn.plone.org/svn/collective/collective.dancing/buildout-extends/0.9.0.cfg
         parts =
             zope2
             ...
             ...
        
         Should you already have an ``extends =`` line, add the new line at
         the end of the other extends files.  For Plone 3.2.2, your
         ``[buildout]`` section might start like this::
      
         [buildout]
         extends =
             http://dist.plone.org/release/3.2.2/versions.cfg
             https://svn.plone.org/svn/collective/collective.dancing/buildout-extends/0.9.0.cfg
         parts =
             zope2
             ...
             ...

  2) Next, you'll need to add ``collective.dancing`` to the ``eggs`` and
     ``zcml`` options in your ``[instance]`` section.  Which should then look 
     like this::
    
         [instance]
         ...
         eggs =
             ${buildout:eggs}
             ...
             collective.dancing
         zcml =
             ...
             collective.dancing
             
     Note: When you are using Plone > 3.3 you can skipt the zcml part, because
     ``z3c.autoinclude`` is shipped with Plone 3.3.x by default.
     

  3) Remove all ``additional-fake-eggs`` and ``skip-fake-eggs`` options
     from your ``[zope2]`` section, if any.  (This is so you don't
     overrride the ones defined in the S&D extends file that we added in
     step 1.)

* Plone 4.x

  1) On Plone 4 you don't need to extend your buildout configuration using
     `extends=...``. You'll need to add ``collective.dancing`` to the ``eggs`` 
     in your ``[instance]`` section.  Which should then look like this::
    
         [instance]
         ...
         eggs =
             ${buildout:eggs}
             ...
             collective.dancing

Once you're done editing your buildout configuration, don't forget to
run your buildout again before you start up Zope::

  $ ./bin/buildout -v

That's it!  You can now start up your Zope instance, and then install
Singing & Dancing in your Plone site by visiting the *Add-on Products*
site control panel.

Troubleshooting
---------------

Should the above instructions not work for you, `contact us`_.

**NOTE**: If you're upgrading your buildout from an older version
where you included version dependencies of S&D by hand, remove the
``develop-eggs`` directory inside your buildout and re-run buildout.

Here's a list of the most common stumbling blocks:

   - `ValueError: too many values to unpack <https://bugs.launchpad.net/singing-dancing/+bug/253377>`_

   - `Products/Five/i18n.zcml uses namespace package in configure package directive <https://bugs.launchpad.net/zope2/+bug/228254>`_

   - Should you see ``ImportError: Module
     zope.app.component.metaconfigure has no global defaultLayer``
     when starting up, make sure you have
     ``plone.recipe.zope2install`` >= 2.2.  You may use buildout's
     ``versions`` feature to tell it which version to use.
     
   - Since version 0.7.0 of collective.singing we don't support older 
     versions of ``z3c.form`` by default. Radio button and checkbox widget 
     hidden templates are already included in more recent ``z3c.form`` 
     versions. ( > 2.3.3 as described here 
     http://pypi.python.org/pypi/z3c.form#id14)
     
     If you want to use an old version (for example the popular 1.9.0 which was 
     pinned in older buildout-extends files) you have to manually include a 
     zcml file located in ``collective.singing.browser.widgets.zcml`` which 
     registers the missing templates for these widgets::
     
        <include package="collective.singing.browser" file="widgets.zcml" />
     
     This fixed https://bugs.launchpad.net/singing-dancing/+bug/620608. 
     
It's installed.  What's next?
-----------------------------

You'll now have an entry in the control panel to *Singing & Dancing*.
This will lead you to to the advanced configuration panel of S&D.

Note that there's already a default newsletter set up for your
convenience.  You can create a *Mailing-list subscribe portlet* to enable
your users to subscribe to this channel, or you can point them to
http://yoursite/portal_newsletters/channels/default-channel/subscribe.html

To send out a newsletter, go to any portal object, like the Plone
front page, and click *Actions -> Send as newsletter*.

The advanced configuration panel of S&D gives you many more ways to
send newsletters, like periodically and from automatically collected
content.

Make sure to also check out our `guide with screenshots`_ for more
details.

Processing the message queue
----------------------------

One important thing to note is that S&D usually queues messages in its
own message queue before sending them out.  You might have noticed
that when you send out a newsletter, S&D tells you that it queued the
messages.

In a production setup, you would normally process the message queue
periodically using the built-in Zope ClockServer_.  While you're
testing, you can visit the *Statistics* screen in the S&D advanced
configuration panel and manually clear the queues.  If your mail
configuration in Plone is set up correctly, you should be sending mail
out now.

To set up ClockServer to trigger the processing automatically for you,
add this stanza to the Zope 2 ``[instance]`` section of your buildout
configuration and rerun ``bin/buildout -v``::

  zope-conf-additional = 
      <clock-server>
        # plonesite is your plone path
        method /plonesite/@@dancing.utils/tick_and_dispatch
        period 300
        user admin
        password admin
        # You need your *real* host here
        host www.mysite.com 
      </clock-server>
      
Or, if your site is behind Apache using a Virtual Host, 
the zope.conf clock server configuration would be ::

  zope-conf-additional = 
      <clock-server>
        # plonesite is your plone path
        # www.mysite.com your site url
        method /VirtualHostBase/http/www.mysite.com:80/plonesite/VirtualHostRoot/@@dancing.utils/tick_and_dispatch
        period 300
        user admin
        password admin
      </clock-server>

This will process the message queue every five minutes.  It assumes
that your Plone site's ID is ``portal``, that your username and
password are ``admin``, and that your site is called
``www.mysite.com``.

**Note**: You must not set up this ClockServer on more than one
instance.  The processing makes sure it's not invoked twice at the
same time by using file locking.  This file locking won't work if you
configure the clock server on two different servers.

Configuring zope.sendmail to send out messages
----------------------------------------------

Singing & Dancing uses `zope.sendmail`_ to send out its mail.  S&D
comes with a default configuration for ``zope.sendmail`` in its
``collective/dancing/mail.zcml`` file.  This configuration will read
SMTP parameters from your Plone site.

Be warned however, that this default configuration is not suitable for
high-volume newsletters.  The aforementioned configuration file
contains an example configuration using ``mail:queuedDelivery`` that
works much more reliably when dealing with a large number of mails.

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

Donate
======

Developing software as Open Source can be a thankless task sometimes.
If you're a happy user of Singing & Dancing, and you'd like to show your
appreciation, you might want to `donate via PayPal`_.

There's other ways to contribute to the project if you're not a
developer; one is to post a message to the `mailing list`_ describing
any successes or problems that you have with the software.  That's the
only way we can know if S&D is working correctly for you.  Another is
to add a screenshot to the `sites using S&D`_.

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


.. _guide with screenshots: http://groups.google.com/group/singing-dancing/web/singing-dancing-screenshots
.. _Python eggs on PyPI: http://pypi.python.org/pypi/collective.dancing
.. _depend: http://peak.telecommunity.com/DevCenter/setuptools#declaring-dependencies
.. _buildout: http://pypi.python.org/pypi/zc.buildout
.. _how to create a buildout: http://plone.org/documentation/tutorial/buildout/creating-a-buildout-for-your-project
.. _follow this tutorial: http://plone.org/documentation/tutorial/buildout
.. _ClockServer: http://plope.com/software/ClockServer/
.. _let us know: http://bugs.launchpad.net/singing-dancing/+filebug
.. _zope.sendmail: http://pypi.python.org/pypi/zope.sendmail
.. _mailing list: http://groups.google.com/group/singing-dancing
.. _Freenode: http://freenode.net
.. _donate via PayPal: http://ur1.ca/2d41
.. _sites using S&D: http://ur1.ca/2d4p
.. _interfaces.py: http://dev.plone.org/collective/browser/collective.singing/trunk/collective/singing/interfaces.py
.. _Subversion repository: http://svn.plone.org/svn/collective/collective.dancing/trunk#egg=collective.dancing-dev
