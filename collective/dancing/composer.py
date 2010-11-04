# --*-- coding: utf-8 --*--
import atexit
import datetime
import logging
import inspect
import md5
import re
import os
import string
import tempfile
from email.Utils import formataddr
from email.Header import Header

from BeautifulSoup import BeautifulSoup

import persistent
from ZODB.POSException import ConflictError
from zope import interface
from zope import component
from zope import schema
import zope.annotation.interfaces
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
import zope.app.component.hooks
import zope.sendmail.mailer
import zope.publisher.interfaces.browser
import Products.CMFCore.interfaces
import Products.CMFPlone.interfaces
import collective.singing.interfaces
import collective.singing.mail

from collective.dancing import MessageFactory as _
from collective.dancing import transform
from collective.dancing import utils

from interfaces import IFullFormatter
from interfaces import IHTMLComposer
from interfaces import IHTMLComposerTemplate

from plone.memoize import volatile

logger = logging.getLogger('collective.singing')

class InvalidEmailAddress(schema.ValidationError):
    _(u"Your e-mail address is invalid")
    regex = r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"

def check_email(value):
    """
      >>> def t(value):
      ...    try:
      ...        return check_email(value)
      ...    except InvalidEmailAddress:
      ...        return False

    Some common examples.

      >>> t('tmog@domain.tld')
      True
      >>> t('t.mog@domain.tld')
      True
      >>> t('t-mog@subdomain.domain.tld')
      True
      >>> t('tmog@sub-domain.domain.tld')
      True

    Note that we only accept real-world routeable addresses

      >>> t('tmog@localhost')
      False

    We also do not accept capitals.

      >>> t('TMOG@domain.TLD')
      False
      >>> t('Tmog@domain.tld')
      False
      >>> t('TMOG@DOMAIN.TLD')
      False

    This passed with the old regex.

      >>> t('tmog@domain.tld.')
      False

    More fails.

      >>> t('tmog@domain@tld')
      False
      >>> t('tmog.domain.tld')
      False
      >>> t('tmog')
      False

    No international chars plz.

      >>> t('René@la-resistance.fr')
      False

    """
    if not re.match(InvalidEmailAddress.regex, value):
        raise InvalidEmailAddress
    # Lazy: Not adding this final check to the regexp.
    return not value.endswith('.')

class PrimaryLabelTextLine(schema.TextLine):
    interface.implements(collective.singing.interfaces.ISubscriptionKey,
                         collective.singing.interfaces.ISubscriptionLabel)

    def fromUnicode(self, str):
        str = str.lower().strip()
        return super(PrimaryLabelTextLine, self).fromUnicode(str)

def _render_cachekey(method, self, vars, items):
    return (vars, items)

def template_var(varname):
    """Should return a string that is unlikely to occur in the
    rendered newsletter.  This could be made a lot more unlikely.
    Remember the result must be a valid, single string.Template
    variable name.
    """
    return '%s%s' % ('composervariable', varname)

class IHTMLComposerSchema(interface.Interface):
    email = PrimaryLabelTextLine(title=_(u"E-mail address"),
                                 constraint=check_email)

@component.adapter(collective.singing.interfaces.ISubscription)
@interface.implementer(IHTMLComposerSchema)
def composerdata_from_subscription(subscription):
    return utils.AttributeToDictProxy(subscription.composer_data)


class HTMLTemplateVocabularyFactory(object):

    interface.implements(schema.interfaces.IVocabularyFactory)

    def __call__(self, context):
        names = [x[0] for x  in component.getUtilitiesFor(IHTMLComposerTemplate)]
        return schema.vocabulary.SimpleVocabulary.fromValues(names)

default_template = ViewPageTemplateFile('browser/composer-html.pt')

class HTMLComposer(persistent.Persistent):
    """
      >>> from zope.interface.verify import verifyClass
      >>> from collective.dancing.interfaces import IHTMLComposer
      >>> verifyClass(IHTMLComposer, HTMLComposer)
      True
    """

    interface.implements(IHTMLComposer)

    title = _(u'HTML E-Mail')
    schema = IHTMLComposerSchema

    encoding = 'utf-8'
    stylesheet = u""
    from_name = u""
    from_address = u""
    replyto_address = u""
    subject = u"${site_title}: ${channel_title}"
    header_text = u"<h1>${subject}</h1>"
    footer_text = u""

    template_name = 'default'
    confirm_template = ViewPageTemplateFile('browser/composer-html-confirm.pt')
    forgot_template = ViewPageTemplateFile('browser/composer-html-forgot.pt')

    @staticmethod
    def secret(data):
        salt = component.getUtility(collective.singing.interfaces.ISalt)
        return md5.new("%s%s" % (data['email'], salt)).hexdigest()

    context = None
    @property
    def request(self):
        site = zope.app.component.hooks.getSite()
        return site.REQUEST

    @property
    def _from_address(self):
        properties = component.getUtility(
            Products.CMFCore.interfaces.IPropertiesTool)
        charset = properties.site_properties.getProperty('default_charset', 'utf-8')

        name = self.from_name or properties.email_from_name
        mail = self.from_address or properties.email_from_address
        if not isinstance(name, unicode):
            name = name.decode(charset)
        if not isinstance(mail, unicode):
            # mail has to be be ASCII!!
            mail = mail.decode(charset).encode('us-ascii', 'replace')
            #TODO : assert that mail is now valid. (could have '?' from repl.)

        return formataddr((str(Header(name, charset)), mail))

    @property
    def language(self):
        return self.request.get('LANGUAGE')

    def _vars(self, subscription, items=()):
        """Provide variables for the template.

        Override this or '_more_vars' in your custom HTMLComposer to
        pass different variables to the templates.
        """
        vars = {}
        site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        site = utils.fix_request(site, 0)
        fix_urls = lambda t: transform.URL(site).__call__(t, subscription)

        vars['channel'] = subscription.channel
        vars['site_url'] = site.absolute_url()
        site_title = site.Title()
        if not isinstance(site_title, unicode):
            site_title = unicode(site_title, 'UTF-8')
        vars['site_title'] = site_title
        vars['channel_title'] = subscription.channel.title
        vars['subject'] = self.subject
        # Why would header_text or footer_text ever be None?
        vars['header_text'] = fix_urls(self.header_text or u"")
        vars['footer_text'] = fix_urls(self.footer_text or u"")
        vars['stylesheet'] = self.stylesheet
        vars['from_addr'] = self._from_address
        headers = vars['more_headers'] = {}
        if self.replyto_address:
            headers['Reply-To'] = self.replyto_address

        # This is so brittle, it hurts my eyes.  Someone convince me
        # that this needs to become another component:
        for index, item in enumerate(items):
            formatted, original = item
            title = getattr(original, 'Title', lambda: formatted)()
            vars['item%s_title' % index] = title

        vars.update(self._more_vars(subscription, items))

        def subs(name):
            vars[name] = string.Template(vars[name]).safe_substitute(vars)
        for name in 'subject', 'header_text', 'footer_text':
            subs(name)

        # It'd be nice if we could use an adapter here to override
        # variables.  We'd probably want to pass 'items' along to that
        # adapter.

        return vars

    def _more_vars(self, subscription, items):
        """Less generic variables.
        """
        vars = {}
        channel = subscription.channel
        site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        site = utils.fix_request(site, 0)
        secret_var = '$%s' % template_var('secret')
        vars['confirm_url'] = (
            '%s/confirm-subscription.html?secret=%s' %
            (site.portal_newsletters.absolute_url(), secret_var))
        vars['unsubscribe_url'] = (
            '%s/unsubscribe.html?secret=%s' %
            (channel.absolute_url(), secret_var))
        vars['my_subscriptions_url'] = (
            '%s/../../my-subscriptions.html?secret=%s' %
            (channel.absolute_url(), secret_var))
        vars['to_addr'] = '$%s' % template_var('to_addr')
        return vars

    def _subscription_vars(self, subscription):
        """Variables that are expected to be unique
        to every subscription.
        """
        vars = {}
        vars[template_var('secret')] = self.secret(subscription.composer_data)
        vars[template_var('to_addr')] = subscription.composer_data['email']
        for k, v in subscription.composer_data.items():
            vars[template_var(k)] = v
        return vars

    @volatile.cache(_render_cachekey)
    def _render(self, vars, items):
        if getattr(self, 'template', None) is not None:
            # This instance has overridden the template attribute.
            # We'll use that template. Note that this will be a bound template,
            # so we will need to "unbind" it by accessing im_func directly.
            template = self.template.im_func
        else:
            template = component.getUtility(IHTMLComposerTemplate, name=self.template_name)
        html = template(
            self,
            contents=[i[0] for i in items],
            items=[dict(formatted=i[0], original=i[1]) for i in items],
            **vars)
        return utils.compactify(html)

    def render(self, subscription, items=(), override_vars=None):
        vars = self._vars(subscription, items)
        subscription_vars = self._subscription_vars(subscription)

        if override_vars is None:
            override_vars = {}
        vars.update(override_vars)

        html = self._render(vars, items)
        html = string.Template(html).safe_substitute(subscription_vars)

        message = collective.singing.mail.create_html_mail(
            vars['subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=subscription_vars[template_var('to_addr')],
            headers=vars.get('more_headers'),
            encoding=self.encoding)

        return collective.singing.message.Message(
            message, subscription)

    def render_confirmation(self, subscription):
        vars = self._vars(subscription)
        subscription_vars = self._subscription_vars(subscription)

        if 'confirmation_subject' not in vars:
            vars['confirmation_subject'] = zope.i18n.translate(
                _(u"Confirm your subscription with ${channel-title}",
                  mapping={'channel-title': subscription.channel.title}),
                target_language=self.language)

        html = self.confirm_template(**vars)
        html = utils.compactify(html)
        html = string.Template(html).safe_substitute(subscription_vars)

        message = collective.singing.mail.create_html_mail(
            vars['confirmation_subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=subscription_vars[template_var('to_addr')],
            headers=vars.get('more_headers'),
            encoding=self.encoding)

        # status=None prevents message from ending up in any queue
        return collective.singing.message.Message(
            message, subscription, status=None)

    def render_forgot_secret(self, subscription):
        vars = self._vars(subscription)
        subscription_vars = self._subscription_vars(subscription)

        if 'forgot_secret_subject' not in vars:
            vars['forgot_secret_subject'] = zope.i18n.translate(
                _(u"Change your subscriptions with ${site_title}",
                  mapping={'site_title': vars['site_title']}),
                target_language=self.language)

        html = self.forgot_template(**vars)
        html = utils.compactify(html)
        html = string.Template(html).safe_substitute(subscription_vars)

        message = collective.singing.mail.create_html_mail(
            vars['forgot_secret_subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=subscription_vars[template_var('to_addr')],
            headers=vars.get('more_headers'),
            encoding=self.encoding)

        # status=None prevents message from ending up in any queue
        return collective.singing.message.Message(
            message, subscription, status=None)

plone_html_strip_not_likey = [
    {'id': 'review-history'},
    {'class':'documentActions'},
    {'class':'portalMessage'},
    {'id':'plone-document-byline'},
    {'id':'portlets-below'},
    {'id':'portlets-above'},
    {'class': 'newsletterExclude'},
    ]
def plone_html_strip(html, not_likey=plone_html_strip_not_likey):
    r"""Tries to strip the relevant parts from a Plone HTML page.

    Looks for ``<div id="content">`` and ``<div id="region-content">`` as
    a fallback.

      >>> html = (
      ...     '<html><body><div id="content"><h1 class="documentFirstHeading">'
      ...     'Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      ...     '</div></body></html>')
      >>> plone_html_strip(html)
      u'<h1 class="documentFirstHeading">Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      >>> plone_html_strip('<div id="region-content">Hello, World!</div>')
      u'Hello, World!'

    Will also strip away any ``<div id="review-history">``:

      >>> html = (
      ...     '<div id="region-content">'
      ...     '<div id="review-history">Yesterday</div>Tomorrow</div>')
      >>> plone_html_strip(html)
      u'Tomorrow'

    """
    if not isinstance(html, unicode):
        html = unicode(html, 'UTF-8')

    soup = BeautifulSoup(html)
    content = soup.find('div', attrs={'id': 'content'})
    if content is None:
        content = soup.find('div', attrs=dict({'id': 'region-content'}))

    for attrs in not_likey:
        for item in content.findAll(attrs=attrs):
            item.extract() # meaning: item.bye()
    return content.renderContents(encoding=None) # meaning: as unicode

class CMFDublinCoreHTMLFormatter(object):
    """Render a brief representation of an IBaseContent for HTML.
    """
    interface.implements(collective.singing.interfaces.IFormatItem)
    component.adapts(Products.CMFCore.interfaces.IMinimalDublinCore,
                     zope.publisher.interfaces.browser.IBrowserRequest)

    template = """\
    <div>
      <h2><a href="%(url)s">%(title)s</a></h2>
      <p>%(description)s</p>
    </div>
    """

    def __init__(self, item, request):
        self.item = item
        self.request = request

    def __call__(self):
        i = self.item
        return self.template % dict(
            url=i.absolute_url(), title=i.Title(), description=i.Description())

class PloneCallHTMLFormatter(object):
    """Assumes that item is callable and returns an HTML
    representation.

    If what ``item()`` returns looks like a rendered Plone page, this
    formatter will try and strip away all irrelevant parts.
    """

    interface.implements(collective.singing.interfaces.IFormatItem)

    def __init__(self, item, request):
        self.item = item

    def __call__(self):
        try:
            html = self.item()
        except ConflictError:
            raise
        except:
            # Simple calling does not work if layout
            # is a view, we can try a little harder...
            html = self.item.unrestrictedTraverse(self.item.getLayout())()
        if 'kss' in html:
            return plone_html_strip(html)
        else:
            return html

class FullFormatWrapper(object):
    """Wraps an item for use with a full formatter."""

    def __init__(self, item):
        self.item = item

    def __getattr__(self, key):
        return getattr(self.item, key)

class HTMLFormatItemFully(object):
    interface.implements(collective.singing.interfaces.IFormatItem)

    def __init__(self, wrapper, request):
        self.item = wrapper.item
        self.request = request

    def __call__(self):
        view = component.getMultiAdapter(
            (self.item, self.request), IFullFormatter, name='html')

        return view()

class SMTPMailer(zope.sendmail.mailer.SMTPMailer):
    """A mailer for use with zope.sendmail that fetches settings from
    the Plone site's configuration.
    """
    def _fetch_settings(self):
        root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        m = root.MailHost
        return dict(hostname=m.smtp_host or 'localhost',
                    port=m.smtp_port,
                    username=m.smtp_uid or None,
                    password=m.smtp_pwd or None,)

    def send(self, fromaddr, toaddrs, message):
        self.__dict__.update(self._fetch_settings())
        return super(SMTPMailer, self).send(fromaddr, toaddrs, message)

class StubSMTPMailer(zope.sendmail.mailer.SMTPMailer):
    """An ISMPTMailer that logs what it would do and reports a status
    upon application exit.
    """

    logfile = None
    sent = 0
    recipients = set()

    def __init__(self, *args, **kwargs):
        super(StubSMTPMailer, self).__init__(*args, **kwargs)
        path = os.path.join(tempfile.gettempdir(),
                            'collective.dancing.StubSMTPMailer.log')
        StubSMTPMailer.logfile = logfile = open(path, 'a')

        logger.info("%r logging to %s" % (self, path))
        self.log("StubSMTPMailer starting to log.")

    def send(self, fromaddr, toaddrs, message):
        self.log("StubSMTPMailer.send From: %s, To: %s\n" % (fromaddr, toaddrs))
        StubSMTPMailer.sent += 1

        for addr in toaddrs:
            self.recipients.add(addr)

    @staticmethod
    def log(msg):
        text = msg.encode('utf-8')
        StubSMTPMailer.logfile.write(
            "%s: %s\n" % (datetime.datetime.now(), text))
        StubSMTPMailer.logfile.flush()

@atexit.register
def at_exit():
    if StubSMTPMailer.logfile is None:
        return
    StubSMTPMailer.log(
        "StubSMTPMailer shutting down, sent %s messages to %s recipients.\n" %
        (StubSMTPMailer.sent, len(StubSMTPMailer.recipients)))
    StubSMTPMailer.logfile.close()
