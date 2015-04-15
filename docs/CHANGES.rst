Changelog
=========

1.0dev (Unreleased)
-------------------

- Don't try to patch ATTopic if ``plone.app.collection`` is available.
  [saily]

- Made all tests pass.
  [saily]

- Add some helper functions to composer which allows ``plone.z3cform``
  to render wysiwyg-widget with TinyMCE on channel edit form which
  passes a composer as context.
  [saily]

- Update buildout(s) and add travis tests for plone 4.0, 4.1, ... 4.3.
  [saily]

- Align package structure to new plone conventions.
  [saily]

- Fix call of ``getSiteManager`` because imports changed from
  ``import zope.component`` to ``from zope import component``.

- plone4.3 compat [kiorky]

- "single subscribe form" now clears secret after
  unsubscribing from all channels. The email address
  is preserved and the user is able to re-subscribe or
  subscribe with another address.
  [tmog]

- Add "Clear pending jobs" button on
  statistics page.
  [tmog]

- Updated danish translations.
  [tmog]

- Add better status message when unsubscribing from all channels
  on "single subscribe form".
  [tmog]

- Key-fields, such as "E-mail address" is now disabled on "single
  form subscription page" when viewing an existing subscription.
  This was misleading anyway, since they could not really be changed.
  [tmog]

- Fix #924124: When using "single form subscription page"
  User email no longer leaks into the default text of "E-mail address"
  in subscribe.html for all sessions after user manages subscription.
  [tmog]

- Fix test breakage with newer versions of zope.testbrowser
  Tested on zope.testbrowser 3.10-3.11.1
  zope.testbrowser-3.11.1 will be pinned in the test buildout
  for now.
  [tmog]

- Fix newsletter queue handling. Now the key to get a newsletter is the UID and not the path.
  In this way, newsletters can be renamed/moved also when they are already in the queue, and
  if they will be erased, the dispatch doesn't breaks.
  [cekk]

- Added two new events, raised when an user confirm or remove his subscription.
  [cekk]

- Fix Italian translations [cekk]

- Added content rules to allow automated sending of content as a newsletter
  [djay]

- "Send as Newsletter" can now be sent to an optionally subscribed section rather
  than the whole channel
  [arterrey]

- External subscriber database and sign up form support
  [ivanteoh]

0.9.10 (2012-02-25)
-------------------

- Fix #363127: persistent utilities will no longer destroy site after
  an uninstall of S&D.
  [nouri]

- remove deprecation warning on plone4.1
  [toutpt]

0.9.9 (2011-07-22)
------------------

- Work around incompatibility with plone.app.z3cform's base template, by
  changing the request in our own `switch_on` function and removing the more
  specialized `IPloneFormLayer`, thus falling back on the layer from
  `plone.z3cform` and its base template.
  Closes https://bugs.launchpad.net/singing-dancing/+bug/697348.
  [hannosch]

0.9.8 (2011-07-21)
------------------

- Replace several untranslatable strings.
  [pfurman]

- Fixed compatibility with Plone 4.1 by (conditionally) loading the
  permissions.zcml from CMFCore.  (Still works on Plone 3.3 and 4.0
  too.)
  [maurits]

- Link to new manual.
  [nouri]

0.9.7 (2011-02-23)
------------------

- Support acquisition-wrapped channel; the possible wrapping of the
  channel object is particularly important with subscriptions since
  the ``five.intid`` utility is used to track them and has delicate
  code to avoid acquisition "loops".
  [malthe]

- Fixed issue that allowed an anonymous user to confirm a random
  subscriber from a channel for which the standard confirm view is
  exposed.
  [malthe]

0.9.6 (2011-02-10)
------------------

- Fixed critical issue that allowed an anonymous user to unsubscribe a
  random subscriber from a channel for which the standard unsubscribe
  view is exposed.
  [malthe]

- Fixed unclosed input tag for including the hidden secret.
  [maurits]

0.9.5 (2010-12-26)
------------------

- Updated the patched `queryCatalog` method of the collection class with
  changes from the baseline.
  [hannosch]

0.9.4 (2010-12-03)
------------------

- Fixed release.

0.9.3 (2010-12-03)
------------------

- Added configuration setting for ``keep_sent_messages`` (new in
  ``collective.singing`` 0.7.1).
  [malthe]

- Fixed CSV Download view for not to break on composers that include list,
  boolean and datetime fields.
  [piv]

- Documentation updates.  [saily]

- Added italian translation, thanks to Augusto Sosa.  [saily]

- Update French translation to reflect change of channel to mailing list
  [toutpt]

0.9.2 (2010-11-04)
------------------

- Documentation updates.   [saily]

- Fixed the stub mailer (encoding issue). [malthe]

0.9.1 (2010-11-04)
------------------

- Fixed the stub mailer (how it ever could work is unclear). [malthe]

- Update test to pass on Plone4
  [toutpt] [pbauer]

- Refactoring send/preview form because formtabbing did not work.
  [saily]

- Reverted changeset 119773 since users could not send folderish content
  types any more (RichDocument is a folderish content type).
  [saily]

0.9.0 (2010-08-01)
------------------

- The send form is now split into two subforms, one for send, and one for
  preview. **NOTE!** This introduces incompatible changes if you are having
  custom forms (although the changes necessary are simple).
  [regebro]

- The "Send as newsletter" action is now no longer shown on folders by
  default.
  [regebro]

- A new 'mass delete from csv' feature has been added to the channel
  administration page. [kiorky]

- French translations have been updated [kiorky]

- "Channels" have been renamed "Mailing-lists" in the userinterface. [regebro]

- Norwegian translation. [regebro]

0.8.17 (2010-06-11)
-------------------

- Fix for subscription portlet breaking batch workflow state change.
  Fixes https://bugs.launchpad.net/singing-dancing/+bug/475771
  [maurits]

- When no address has been selected for sending the preview to, inform
  the user instead of sending the preview to *all* subscribers.
  Fixes https://bugs.launchpad.net/singing-dancing/+bug/509577
  [maurits]

- When compactifying the sent html with stoneagehtml catch an error that
  can occur with some css code, that stoneagehtml tries to clean up
  using cssutils.
  Fixes https://bugs.launchpad.net/singing-dancing/+bug/410238
  [maurits]

- Changed all occurences of site-title to site_title (in help strings
  and translations).
  Fixes https://bugs.launchpad.net/singing-dancing/+bug/296759
  [maurits]

- We now avoid including all zcml from five.intid (in the same way as e.g.
  plone.app.intid) This means we avoid registering the IPersistent handlers,
  which (among other issues) can cause problems for packages that put persistent
  items in temporary storage. Instead we explicitly register handlers for
  ISubscription. The issue is discussed here:
  http://www.mail-archive.com/zodb-dev@zope.org/msg04398.html
  And at length, as pertaining to the getpaid package, here:
  http://code.google.com/p/getpaid/issues/detail?id=209.
  [tmog]

- Reverted changeset 113529 since it broke subscriber searching (and tests).
  The revert has likely reintroduced a problem with deleting subscriptions,
  but I've been unable to reproduce this.
  [tmog]

- When importing email addresses, convert all addresses to lowercase
  instead of rejecting them.
  [maurits]

- Update french translation
  [toutpt]

Version 0.8.16 - 2010-04-07
---------------------------

- Fixed translations that were causing compile errors on Zope startup,
  resulting in old translations showing up for a language (taken from
  the outdated .mo file), or no translations at all.
  [maurits]

- Updated Dutch translations.
  [maurits]

- Fixed a bug that made it impossible to delete some subscriptions.
  [regebro]

Version 0.8.15 - 2010-02-01
---------------------------

- Added a development buildout and automated test runner setup to the package.
  [hannosch]

- Fixed ConfigurationError: ('Missing parameter:', 'description') on Plone 3
  with the last upgrade steps.
  [toutpt]

Version 0.8.14 - 2010-01-28
---------------------------

- Added missing upgrade steps for all recent versions. This makes the package
  comply with the upgrade logic of the Plone add-ons control panel.
  [hannosch]

- Follow best practice and decouple the profile metadata from the software
  version in setup.py.
  [hannosch]

- Added a z3c.autoinclude entry point to mark this as a Plone add-on.
  [hannosch]

- Added our own overrides.zcml to load the one from plone.z3cform. You cannot
  load overrides in the configure stage.
  [hannosch]

- Add log on ATTopic Patch.
  [toutpt]

- Update French translations.
  [toutpt]

- Fix i18n pot file by escape quotes.
  [toutpt]

- Extended the HTML composer so that you can select which composer template
  to use. You register new composer templates by instantiating a template
  somewhere in your code::

    >>> mytemplate = ViewPageTemplateFile('browser/composer-html.pt')

  and registering that in ZCML::

    <utility component=".module.mytemplate"
           name="My Custom Template"
           provides="collective.dancing.interfaces.IHTMLComposerTemplate" />

  [regebro]

Version 0.8.13 - 2009-10-19
---------------------------

- The attribute 'subscribeable' now defaults to False on newly created
  channels. This means newly created channels will not show up on my-subscriptions
  before they are made subscribeable from the channels configuration page.
  [tmog]

- Disabled stoneagehtml style attributes blacklist since it stripped
  out font-familiy from the styles added to a channel which confused
  several users. This fixes http://tinyurl.com/ygmhv7a
  Unfortunately its not possible to specify a custom
  black list like stoneagehtml.compactify(html, filter_tags=['position'...])
  since the stoneagehtml dosen't support that yet - http://tinyurl.com/ykwca4p.
  [pelle]

- Fixed bug that caused the "Include collector items" option to
  be ignored (i.e. always on) in "Send as newsletter" previews.
  Also, there is now a default cue for the dummy preview subscriber.
  The cue is always "one week ago".
  [tmog]

Version 0.8.12 - 2009-09-15
---------------------------

- Changed the email address validation. The old one allowed a few bad
  addresses to slip through - addresses with trailing dots for instance.
  The new validation is generally stricter. Note that 'simple' local addresses
  like 'admin@localhost' are no longer allowed. For special use-cases where you
  need this, you must change the validation RegExp. However, for most usecases, I
  believe this is a big improvement.
  [tmog]

Version 0.8.11 - 2009-09-03
---------------------------

- Added alternative "My subscriptions" page. It's based on a single form
  with subforms, instead of multiple forms like the old one. It's main
  feature is that it displays the ISubscriptionKey (the email address ;-))
  and "subscribe" button only once. It has a checkbox for subscribing to
  each channel.
  To try the new version, select it from the new "Global settings" controlpanel.
  [tmog]

- Translated new messageids for german language and updated some old ones.
  [saily]

Version 0.8.10 - 2009-06-11
---------------------------

- Fix bug where collector sort criteria other than 'created' and
  'effective' would result in an error. [nouri]

- Fixed and added test for newsletter preview form.  The preview in
  the channel page would fail before with ``TypeError: eval() arg 1
  must be a string or code object``. [nouri]

Version 0.8.9 - 2009-03-11
--------------------------

- Fix the bug that Doug found where items from collectors would be
  rendered fully. [nouri]

- Update installation instructions to account for Plone 3.2.x
  buildouts, which are somewhat different. [nouri]

- Added optional keyword argument ``override_vars`` to
  Composer.render.  ``override_vars`` are now a override individual
  ``composer_vars`` from e.g. the ``send-newsletter.html`` form.

  I've included an example of this in the section "Customizing the
  send as newsletter form" in browser.txt (and the new
  ``send-newsletter-custom-subject.html`` view).  This is a pretty
  pervasive change since it needs to work with asynchronous sending,
  email-previewing, browser-previewing, and with scheduled delivery.

  Included is an upgrade step for migrating ``TimedScheduler.items``
  to the new format.  Refer to the Upgrade_ section for details on how
  to run upgrades.  [tmog]

Version 0.8.8 - 2009-02-01
--------------------------

- Fix a dependency issue with collective.singing. [nouri]

Version 0.8.7 - 2009-02-01
--------------------------

- We now have much easier installation instructions. [nouri]

- Fix #313044: Don't mess up ``javascript:`` links when making
  absolute links out of relative ones. [nouri]

Version 0.8.6 - 2009-01-20
--------------------------

- Fix #318725: Don't mess up ``mailto:`` links when making absolute
  links out of relative ones.  Thanks to Scribbles. [nouri]

- Exclude all markup with class ``newsletterExclude`` when sending out
  mail.  This allows for a lo-fi way of marking parts of your template
  for exclusion if you can't be bothered to write your own
  ``IFormatItem``. [nouri]

- Added sort_criteria dict to the collector module. It allows to specify
  different query based on the current cue for different sort criteria.
  [naro]

Version 0.8.5 - 2009-01-05
--------------------------

- Extended the CVS input of subscribers to allow arbitrary CVS fields
  to be stored as part of the subscriptions, and then included in the
  composer output using the ``${composervariableFIELDNAME1}``
  syntax. [russf]

Version 0.8.4 - 2009-01-02
--------------------------

- Added some sensible defaults to
  ``collective.dancing.composer.plone_html_strip`` so that key html is
  filtered out. [pigeonflight]

- Add experimental support for zexp. [nouri]

- Added upgradestep to migrate existing MessageQueues to
  collective.singing.queue.CompositeQueue.
  This fixes slow iteration over large queues and
  extremely slow rendering of the staticstics page.
  [tmog]

Version 0.8.3 - 2008-12-03
--------------------------

- Fix issue with unicodeerrors on statistics page because of bad Job-messages.
  Described in https://bugs.launchpad.net/singing-dancing/+bug/299950
  [tmog]

- Part of Czech translation.
  [naro]

- Improved block structure and added classes and ids. Replaced paras with divs.
  These changes will impact existing CSS.  [russf]

- Use of ``Template().substitute`` will be fatal on any un-escaped where $ will
  occur - like on all recent news items :( safe_substitute behaves properly in
  these cirumstances.  [russf]

- Some refactoring in order to allow for more customized subscription forms.
  [nouri]

- Added french translation.

- Made new job-view ``browser/jobs.pt`` translateable, rebuilt pot file and
  updated german translation.  [saily]

Version 0.8.2 - 2008-11-17
--------------------------

- Fixed a bug in ``HTMLComposer`` where unsubscribe_url could not be substituted
  by template engine because of double dollars in variable name.  [saily]

Version 0.8.1 - 2008-11-14
--------------------------

- Small refactoring of tests to allow for reuse of test infrastructure
  in third party tests. [nouri]

Version 0.8.0 - 2008-11-12
--------------------------

- Added bouncing support: The new utility view
  ``@@dancing.utils/handle_bounce`` takes a list of addresses and
  marks subscriptions as pending when it receives more than two bounce
  notifications.  This has the effect that no more messages are sent
  to that subscription, while the subscription is still present in the
  database. [nouri]

- Added caching to composer rendering.  Caching is done based on
  ``_vars`` and collected items.  Notice that ``composer._vars`` has
  been split into two; ``_vars`` and ``_subscription_vars``. The
  latter containing variables that are likely to be unique to the
  subscription, and the former those that are likely shared across
  multiple subscriptions.

  Rendering is now broken into two step:

  1) Rendering the ``composer-html`` template and compacting the
     resulting html with StoneAgeHTML.  ``_vars`` and collected items
     is available in the template.  This step is cached on ``_vars``
     and items.

  2) ``string.Template`` variable replacement on the html of variables
     in ``_subscription_vars``.  In the default implementation only
     the subscribers secret in the subscription management urls is
     replaced.

  [tmog]

Version 0.7.7 - 2008-11-05
--------------------------

- Set ``ignoreContext = True`` for SubscriptionsSearchForm.  Before
  I'd get ``AttributeError: 'ManageSubscriptionsForm' object has no
  attribute 'fulltext'``, but strangely enough not in the tests and
  only in one installation that I know of.  [nouri]

Version 0.7.6 - 2008-11-05
--------------------------

- German translation has been updated.
  [saily]

- Used i18ndude to find all untranslated msgid's. There were some updates in
  collective.dancing queue-button-naming, so all guy's please help updating
  collective.dancing's po files.  [saily]

- Fixed a bug where when sending a preview we were incorrectly setting
  the ``cue`` of the subscription that the preview is sent to. [nouri]

- Fix #264990: When sending out a newsletter from a content item
  manually, we no longer assemble all message in the course of the
  browser request.  Instead, we schedule a job that's executed
  asynchronously on ``tick_and_dispatch`` time. [nouri]

Version 0.7.5 - 2008-10-27
--------------------------

- Move file locking from queue dispatch to the ``tick_and_dispatch``
  browser view.  This is to make sure that we don't put duplicates
  into the queue.  This is because the underlying queue implementation
  will actually work against us here by allowing simultaneous adds in
  parallel ZODB- writes. [nouri]

- Fix #289779: Strip whitespace from e-mail addresses. [nouri]

- Added ``encoding`` attribute on the ``HTMLComposer`` class to make
  it possible to either subclass and provide a different default
  encoding, or set a persistent attribute. [malthe]

- Fix #280338: Images in header and footer text were sent with
  relative URLs. [nouri]

- It's now possible to filter channels from the sendnewsletter view.
  Simple by setting channel.sendable=False.
  [tmog]

- Fixed an issue with installing collective.dancing from python.
  The event-listener registering ISalt on creation of a new tool
  no longer depends upon having a request. [tmog]

- zope.conf configuration with Virtual Host added in
  documentation [macadames]

Version 0.7.4 - 2008-09-19
--------------------------

- Fix an issue where confirming pending subscriptions by visiting the "My
  subscriptions" page.  If a subscription is already confirmed the dictionary
  ``subscription.metadata`` does not have a key ``pending``.  [saily]

Version 0.7.3 - 2008-09-16
--------------------------

- Rebuild ``collective.dancing.pot`` and updated German
  translation. [saily]

- Removed bug in ``ManageSubscriptionsForm.remove``. When the search box
  was added we also changed the ``ManageSubscriptionsForm.get_items`` method
  to return the secret instead of the name. The remove method was not updated,
  and delete of subscriptions did not work. [saily]

- Removed bug in CSV-export. Export must have same ordered fields or
  columns as expected on import. As we are using the composer schema
  for import, we should use this for export too. [saily]

- Make CSV export and import use the same delimiter.
  [saily]

Version 0.7.2 - 2008-09-15
--------------------------

- Fix an issue where the scheduled send-out would send out items in
  their short form, i.e. only title and description.  [miziodel, nouri]

- Add a search box to the subscriptions administration view.

  Prior versions of S&D didn't populate the subscribers fulltext index
  correctly.  This version adds an upgrade step that you'll need to
  run in order to reindex all your subscription objects.

  Refer to the Upgrade_ section for details on how to run upgrades.
  [nouri]

- Allow pending subscriptions to be conformed by visiting the "My
  subscriptions" page.  This allows users to confirm their
  subscriptions even if they've lost or never received their message
  for confirm.  [nouri]

- More fine-tuning of the ``PloneCallHTMLFormatter``: Strip unwanted
  content like the review history in a configurable way.  [nouri]

Version 0.7.1 - 2008-09-05
--------------------------

- Added workaround for a bug in the composer where ``header_text`` or
  ``footer_text`` are ``None``.  No idea why they're ``None``, though.

Version 0.7.0 - 2008-09-05
--------------------------

- Added a new field ``subject`` for the composer.  This allows more
  control over what subject outgoing messages have, using string
  templates.  The default is ``${site_title}: ${channel_title}``.

  Removed the ``<h1>`` from the default composer template.  You can
  now use the ``header text`` of the composer to the same effect.  The
  default header text has now become ``<h1>${subject}</h1>`` to mimic
  the old behaviour.

  On the API side of things, I changed the signature of
  ``dancing.composer.HTMLComposer._vars``.  Since overriding this is
  the recommended way of providing your own variables, this warrants a
  0.7.0 release.  I'm thinking about adding a little variable provider
  component as an alternative to subclassing.
  [nouri]

- Added missing header with containing style and title tag in
  ``composer-html-forgot.pt`` and ``composer-html-confirm.pt``.
  [saily]

Version 0.6.5 - 2008-09-04
--------------------------

- Add header and footer fields for the composer and its form.  This
  allows us to add text at the beginning and at the end of messages in
  an easy and consistent way. [nouri]

- Fix #264694: Using non ASCII characters in context title
  of send-newsletter raises ``UnicodeEncodeError``. [saily]

- Make ``PloneCallHTMLFormatter`` even more robust by switching to
  using ``BeautifulSoup`` instead of ``str.find`` to parse the
  contents. [nouri]

Version 0.6.4 - 2008-09-03
--------------------------

- Added a default ITransform adapter for S&D called
  ``dancing.transform.URL``.  This will rewrite relative links and the
  like automatically.  Relative links were the cause of broken links
  and images in the outgoing messages.  This fixes #262633.

  What this transform also allows is the definition of one or more
  backend URLs that it should replace by a canonical URL.  See
  ``transform.txt`` for details. [tmog, nouri]

- Fix #262612: The Reply-To field is not included as message header.

Version 0.6.3 - 2008-09-01
--------------------------

- Have the S&D SMTPMailer subclass from zope.sendmail's.  This allows
  the use of TLS with the standard configuration and fixes #263271.

Version 0.6.2 - 2008-08-28
--------------------------

- Updated docs with information on how to configure
  ``mail:queuedDelivery`` of ``zope.sendmail``. [nouri]

- Make the ``PloneCallHTMLFormatter`` which is the fallback formatter
  for all objects more robust. [tmog]

- Improve internationalization with newsletter object titles. [tmog]

- Fixed a bug in csv-export if you use more composer_data than just
  email address. [saily]

- Some people have reported that S&D is sending out duplicate mails on
  high-traffic newsletters.  I've added a ``StubSMTPMailer`` utility,
  which you can register conveniently in
  ``collective/dancing/mail.zcml``.  No mail will be sent out when
  it's configured instead of the default one.  This allows you to
  debug and fine-tune settings, e.g. those of your configured
  ``mail:queuedDelivery`` component. [nouri]

- Changed batch_size in browser/channel.py to 30 to stay at Plone's
  default. [saily]

- German translation updated. [saily]

- Rebuild of collective.dancing.pot using i18ndude. Some translation
  updates needed. [saily]

Version 0.6.1 - 2008-08-22
--------------------------

- On reinstall, advise QuickInstaller not to delete the five.intid
  tool that we set up during installation.  This fixes the brokenness
  of the subscription catalogs after a reinstall.  A typical error
  you'd see would look like::

    ...
     Module collective.singing.subscribe, line 227, in subscription_modified
     Module collective.singing.subscribe, line 214, in _catalog_subscription
     Module five.intid.intid, line 36, in getId
     Module zope.app.intid, line 86, in getId
    KeyError: SimpleSubscription ...

  No migration is available at this point.  Contact us if you need
  help writing one.  Note that the use of QuickInstaller
  reinstallation isn't required with Singing & Dancing.  For how to
  run upgrades from one version to the next, please see the Upgrade_
  section.  A QuickInstaller reinstallation will not run these
  upgrades for you.  [nouri]

Version 0.6.0 - 2008-08-21
--------------------------

- Update to use Singing's new IMessageAssemble API. [nouri]

- Use batching for the subscriptions management view.  Also, reshuffle
  the order of tabs in the channel administration view.  Most notably:
  move the "Subscriptions" tab to the first position to allow more
  comfortable editing. [nouri]

Version 0.5.1 - 2008-08-15
--------------------------

- Fixed a bug where a collector would have a ``Title`` property; this
  should be a method. [malthe]

- Added permissions to send, preview and manage newsletter. No upgrade
  steps required - just reinstall. By default - send and preview is
  allowed to reviewer and manager role, manage newsletters for
  managers only. [saily]

Version 0.5.0 - 2008-07-29
--------------------------

- Display a more user friendly error message when the user attempts to
  add duplicate subscriptions.
  [miziodel, nouri]

- List of subscribers can now be uploaded and downloaded in CSV format!
  [skatja]

- Depend on 0.3 or higher of plone.app.z3cform.
  [nouri]

Version 0.4.1 - 2008-07-23
--------------------------

- Fix ``RuntimeError: maximum recursion depth exceeded`` error in
  ``Module collective.dancing.browser.portlets.channelsubscribe, line
  253, in channel`` when displaying portlets that were created prior
  to 0.4b4.
  [nouri]

Version 0.4 - 2008-07-23
------------------------

New features
~~~~~~~~~~~~

- Added subject, confirmation_subject and forgot_secret_subject to
  vars of composer for easy customization.  Defaults are unchanged.
  [tmog]

- Added sender name, sender address and reply-to address as per
  composer configuration. Composer configuration is now available
  in the new Composers fieldset of the channel edit view.
  [tmog]

- Allow for easier subclassing of HTMLComposer.  The ``_vars()``
  method is now more generally applicable and easily to override.
  [nouri]

- Made adding thirdparty Channels possible. This works the same as
  with Collectors - you simply implement you custom channel and add
  a factory to the collective.dancing.channel.channels list.
  Preview and edit forms are now class methods on ManageChannelView
  to make it easier to subclass for your custom channels.
  [tmog]

- Pass on raw item as received from the collector to the composer
  (template).  Making use of this raw item will obviously bind the
  implementation of the composer to that of the collector.  However,
  it's considered useful for custom implementations that need total
  control and that know what collector they'll be using.

  This required an API change in IComposer.render(); the ``items``
  argument is now a list of 2-tuples instead of a list of formatted
  items.
  [nouri]

- Added Polish translation by Barbara Struk
  [naro]

- Added another type of scheduler: TimedScheduler.  This one allows to
  schedule a number of send-outs with an exact datetime.  Its main use
  is for the "send newsletter" form on a context where we want to
  specify a send-out date in the future.
  [nouri]

- The confirmation view will now confirm pending subscriptions to any
  channel.  This saves us from having to send a separate confirmation
  e-mail for every channel a user subscribes to.  This feature isn't
  used anywhere in S&D core at this point, but it's useful if you're
  writing custom subscription forms.
  [nouri]

- Added SubjectsCollectorBase template class that you can use to
  create a collector based on a vocabulary.  This vocabulary may come
  from anywhere, like from ATVocabularyManager or from the list of all
  subjects/tags available in your site.
  [nouri]

- Text fields will now per default not be included in the resulting
  message if there are no sibling collectors that produced items.
  E.g. if you have a heading text and a sibling topic collector, the
  heading won't appear if the topic didn't return any items.
  [nouri]

Bugfixes
~~~~~~~~

- Updated installation instructions to use the ``fake-zope-eggs``
  feature of the ``plone.recipe.zope2install`` instead of
  ``fakezope2eggs``.  Also, added ``skip-fake-eggs`` to accommodate
  latest changes in ``plone.z3cform``.

- Use ``CompositeQueue`` instead of the simple zc.queue.Queue for
  queueing and archiving mails.  This should help with memory bloat
  when there's a lot of messages in the queue.
  [nouri]

- Don't attempt to do any workflow transition with ATTopic items
  created in the collector; the default workflow will do fine, and we
  avoid errors when using workflows other than the default one.
  [nouri]

- Don't bail if no items are available for preview.
  [malthe]

Version 0.3 - 2008-06-03
------------------------

New features
~~~~~~~~~~~~

- Add translations to German.
  [saily]

- Added preview also to channel view.  This was previously only
  available for the "send as newsletter" action.
  [malthe]

- Refactored channels management view and the dedicated channel view.
  Big improvements to usability of the channel view.
  [malthe]

- Added capability to embed stylesheets in outgoing mail.  Right now,
  this is a simple text field that can be set on the channel's composer.
  We're now making use of the StoneAgeHTML library to embed styles in
  the individual HTML elements instead of providing styles in the
  ``<head>`` of the HTML document.  This gives us much better support
  with quirky e-mail clients out there.
  [malthe]

  In the future, we want to extend this to allow administrators to
  select themes for individual channels by browsing and selecting from a
  list of registered styles.

- Added Czech translation.
  [naro]

- Refactored ``mail.py`` to create ``MIMEMultipart`` based messages.
  This allows us to easily adapt the mail sending process to embed
  images and the like.
  [naro]

- Added a "reference collector".  This allows you to select individual
  portal items to be sent out, as opposed to items collected by a Smart
  Folder or the like.
  [malthe]

Bugfixes
~~~~~~~~

- S&D 0.3b2 introduced an incompatible change with channels created in
  0.3b1 and earlier.  I added a GenericSetup upgrade step to fix this.
  The relevant code is in the ``collective.dancing.upgrade`` module.

  If you're using a legacy database with channels that were created
  before version 0.3b2, you'll need to run this upgrade step, or
  you'll see this error::

    TypeError: ('object.__new__(HTMLComposer) is not safe, use persistent.Persistent.__new__()', <function _reconstructor at ...>, (<class 'collective.dancing.composer.HTMLComposer'>, <type 'object'>, None))

  Refer to the Upgrade_ section for details on how to run upgrades.
  [nouri]

- Add ``metadata.xml`` to make QuickInstaller happy with version
  numbers.
  [naro]

- Back to using checkboxes for multi selection instead of ``select``.
  [nouri]

- Make HTMLComposer and channel.composers persistent so that changes
  to template and composers are conveniently persisted.
  [nouri]

- Use ``zc.lockfile`` to lock the queue processing (sending out of mail)
  instead of excessively using ``transaction.commit()``, which caused
  massive ZODB bloat when a lot of messages were involved.
  [nouri]

- Use ``email.Header`` for message header formatting.  This allows for
  better internationalization in headers of outgoing e-mails.
  [naro]

- In-browser preview now displays what would really be sent out,
  i.e. after collectors and transforms could do their thing.  Before, it
  used to only display the context item as mail.
  [malthe]

Version 0.2 - 2008-05-06
------------------------

- Add an 'Already subscribed?" section to the "My subscriptions"
  page to retrieve your password.
  [nouri]

- added i18n:domain to browser/controlpanel-links.pt, removed extra quotes
  from browser/channel.py, updated pot and danish translation
  [bartholdy]

- updated .pot and danish translation
  [bartholdy]

- apparently triplequoted strings do not get translated ..
  this takes care of
  https://bugs.launchpad.net/singing-dancing/+bug/218448
  [bartholdy]

- Don't use locale-dependent 'string.letters' when creating the
  ISalt utility.  This fixes
  https://bugs.launchpad.net/singing-dancing/+bug/217823
  [nouri]

- Extended portlet with optinal footertext
  [bartholdy]

- Added functionality to show a preview in the browser
  [malthe]
