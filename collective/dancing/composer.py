import atexit
import datetime
import logging
import md5
import re
import os
import tempfile
from email.Utils import formataddr
from email.Header import Header

import stoneagehtml
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
from collective.dancing import utils

from interfaces import IFullFormatter
from interfaces import IHTMLComposer

logger = logging.getLogger('collective.singing')

class InvalidEmailAddress(schema.ValidationError):
    _(u"Your e-mail address is invalid")
    regex = r"[a-zA-Z0-9._%-]+@([a-zA-Z0-9-]+\.)*[a-zA-Z]{2,4}"

def check_email(value):
    if not re.match(InvalidEmailAddress.regex, value):
        raise InvalidEmailAddress
    return True

class PrimaryLabelTextLine(schema.TextLine):
    interface.implements(collective.singing.interfaces.ISubscriptionKey,
                         collective.singing.interfaces.ISubscriptionLabel)

    def fromUnicode(self, str):
        value = super(PrimaryLabelTextLine, self).fromUnicode(str)
        return value.lower()


class IHTMLComposerSchema(interface.Interface):
    email = PrimaryLabelTextLine(title=_(u"E-mail address"),
                                 constraint=check_email)

@component.adapter(collective.singing.interfaces.ISubscription)
@interface.implementer(IHTMLComposerSchema)
def composerdata_from_subscription(subscription):
    return utils.AttributeToDictProxy(subscription.composer_data)

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

    stylesheet = u""
    from_name = u""
    from_address = u""
    replyto_address = u""
    header_text = u""
    footer_text = u""
    
    template = ViewPageTemplateFile('browser/composer-html.pt')
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

        return formataddr((str(Header(name, charset)), mail))

    @property
    def language(self):
        return self.request.get('LANGUAGE')        

    def _vars(self, subscription):
        """Provide variables for the template.

        Feel free to override this to pass more variables to your
        template when you make a custom subclass of HTMLComposer."""
        vars = {}
        site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        site = utils.fix_request(site, 0)
        
        vars['channel'] = subscription.channel
        vars['site_title'] = unicode(site.Title(), 'UTF-8')
        vars['channel_title'] = subscription.channel.title
        vars['from_addr'] = self._from_address
        vars['to_addr'] = subscription.composer_data['email']
        vars['header_text'] = self.header_text
        vars['footer_text'] = self.footer_text
        headers = vars['more_headers'] = {}
        if self.replyto_address:
            headers['Reply-To'] = self.replyto_address

        vars.update(self._more_vars(subscription))
        return vars

    def _more_vars(self, subscription):
        """Less generic variables.
        """
        vars = {}
        channel = subscription.channel
        site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        site = utils.fix_request(site, 0)

        vars['confirm_url'] = (
            '%s/confirm-subscription.html?secret=%s' %
            (site.portal_newsletters.absolute_url(), subscription.secret))
        vars['unsubscribe_url'] = (
            '%s/unsubscribe.html?secret=%s' %
            (channel.absolute_url(), subscription.secret))
        vars['my_subscriptions_url'] = (
            '%s/../../my-subscriptions.html?secret=%s' %
            (channel.absolute_url(), subscription.secret))
        return vars

    def render(self, subscription, items=()):
        vars = self._vars(subscription)
        secret = self.secret(subscription.composer_data)

        if 'subject' not in vars:
            vars['subject'] = zope.i18n.translate(
                _(u"${site-title}: ${channel-title}",
                  mapping={'site-title': vars['site_title'],
                           'channel-title': vars['channel_title']}),
                target_language=self.language)
        
        html = self.template(
            contents=[i[0] for i in items],
            items=[dict(formatted=i[0], original=i[1]) for i in items],
            stylesheet=self.stylesheet,
            **vars)

        html = stoneagehtml.compactify(html).decode('utf-8')

        message = collective.singing.mail.create_html_mail(
            vars['subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=vars['to_addr'],
            headers=vars.get('more_headers'))

        return collective.singing.message.Message(
            message, subscription)

    def render_confirmation(self, subscription):
        vars = self._vars(subscription)

        if 'confirmation_subject' not in vars:
            vars['confirmation_subject'] = zope.i18n.translate(
                _(u"Confirm your subscription with ${channel-title}",
                  mapping={'channel-title': subscription.channel.title}),
                target_language=self.language)

        html = self.confirm_template(**vars)
        
        message = collective.singing.mail.create_html_mail(
            vars['confirmation_subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=vars['to_addr'],
            headers=vars.get('more_headers'))

        # status=None prevents message from ending up in any queue
        return collective.singing.message.Message(
            message, subscription, status=None)

    def render_forgot_secret(self, subscription):
        vars = self._vars(subscription)
        
        if 'forgot_secret_subject' not in vars:
            vars['forgot_secret_subject'] = zope.i18n.translate(
                _(u"Change your subscriptions with ${site-title}",
                  mapping={'site-title': vars['site_title']}),
                target_language=self.language)

        html = self.forgot_template(**vars)

        message = collective.singing.mail.create_html_mail(
            vars['forgot_secret_subject'],
            html,
            from_addr=vars['from_addr'],
            to_addr=vars['to_addr'],
            headers=vars.get('more_headers'))

        # status=None prevents message from ending up in any queue
        return collective.singing.message.Message(
            message, subscription, status=None)

def plone_html_strip(html):
    r"""Tries to strip the relevant parts from a Plone HTML page.

    Looks for ``<div id="content">``, and, as a fallback, for all siblings of
    ``<h1 class="documentFirstHeading">``.

      >>> html = (
      ...     '<html><body><div id="content"><h1 class="documentFirstHeading">'
      ...     'Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      ...     '</div></body></html>')
      >>> plone_html_strip(html)
      u'<h1 class="documentFirstHeading">Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      >>> html = '<div>' + plone_html_strip(html) + '</div>'
      >>> plone_html_strip(html)
      u'<h1 class="documentFirstHeading">Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      >>> plone_html_strip('<div id="region-content">Hello, World!</div>')
      u'Hello, World!'
    """
    if not isinstance(html, unicode):
        html = unicode(html, 'UTF-8')

    soup = BeautifulSoup(html)
    content = soup.find('div', attrs={'id': 'content'})
    if content is None:
        content = soup.find('h1', attrs=dict({'class': 'documentFirstHeading'}))
        if content is not None:
            content = content.parent
    if content is None:
        content = soup.find('div', attrs=dict({'id': 'region-content'}))
    return content.renderContents(encoding=None)

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
                    username=m.smtp_userid or m.smtp_uid or None,
                    password=m.smtp_pass or m.smtp_pwd or None,)

    def send(self, fromaddr, toaddrs, message):
        self.__dict__.update(self._fetch_settings())
        return super(SMTPMailer, self).send(fromaddr, toaddrs, message)

class StubSMTPMailer(zope.sendmail.mailer.SMTPMailer):
    """An ISMPTMailer that'll only log what it would do.
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
        self.recipients.add(toaddrs)

    @staticmethod
    def log(msg):
        StubSMTPMailer.logfile.write(
            "%s: %s\n" % (datetime.datetime.now(), msg))
        StubSMTPMailer.logfile.flush()

@atexit.register
def at_exit():
    if StubSMTPMailer.logfile is None:
        return
    StubSMTPMailer.log(
        "StubSMTPMailer shutting down, sent %s messages to %s recipients.\n" %
        (StubSMTPMailer.sent, len(StubSMTPMailer.recipients)))
    StubSMTPMailer.logfile.close()
