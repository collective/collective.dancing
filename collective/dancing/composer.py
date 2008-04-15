import md5
import re
import smtplib

from zope import interface
from zope import component
from zope import schema
import zope.annotation.interfaces
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
import zope.app.component.hooks
import zope.sendmail.interfaces
import zope.publisher.interfaces.browser
import Products.CMFCore.interfaces
import Products.CMFPlone.interfaces
import collective.singing.interfaces
import collective.singing.mail

from collective.dancing import MessageFactory as _
from collective.dancing import utils

from interfaces import IFullFormatter

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

class HTMLComposer(object):
    interface.implements(collective.singing.interfaces.IComposer,
                         collective.singing.interfaces.IComposerBasedSecret)

    title = _(u'HTML E-Mail')
    schema = IHTMLComposerSchema

    template = ViewPageTemplateFile('browser/composer-html.pt')
    confirm_template = ViewPageTemplateFile('browser/composer-html-confirm.pt')

    @staticmethod
    def secret(data):
        salt = component.getUtility(collective.singing.interfaces.ISalt)
        return md5.new(data['email'] + str(salt)).hexdigest()
    
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
        return collective.singing.mail.header(
            u'%s <%s>' %
            (properties.email_from_name.decode(charset),
             properties.email_from_address.decode(charset)),
            encoding='UTF-8')

    def _render_html(self, subscription, items, subject):
        channel = subscription.channel
        secret = self.secret(subscription.composer_data)
        
        unsubscribe_url = (
            '%s/unsubscribe.html?secret=%s' %
            (channel.absolute_url(), subscription.secret))

        html = self.template(
            subject=subject,
            contents=items,
            channel=channel,
            unsubscribe_url=unsubscribe_url)
        return html

    def render(self, subscription, items=()):
        site = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        site_title = unicode(site.Title(), 'UTF-8')

        language = self.request.get('LANGUAGE')
        subject = zope.i18n.translate(
            _(u"${site-title}: ${channel-title}",
              mapping={'site-title': site_title,
                       'channel-title': subscription.channel.title}),
            target_language=language)
        html = self._render_html(subscription, items, subject)

        message = collective.singing.mail.create_html_mail(
            subject,
            html,
            from_addr=self._from_address,
            to_addr=subscription.composer_data['email'])

        return collective.singing.message.Message(
            message, subscription)

    def render_confirmation(self, subscription):
        channel = subscription.channel

        confirm_url = ('%s/confirm-subscription.html?secret=%s' %
                       (subscription.channel.absolute_url(),
                        subscription.secret))

        html = self.confirm_template(channel=channel,
                                     confirm_url=confirm_url)
        language = self.request.get('LANGUAGE')
        subject = zope.i18n.translate(
            _(u"Confirm your subscription with ${channel-title}",
              mapping={'channel-title': subscription.channel.title}),
            target_language=language)

        message = collective.singing.mail.create_html_mail(
            subject,
            html,
            from_addr=self._from_address,
            to_addr=subscription.composer_data['email'])

        # status=None prevents message from ending up in any queue
        return collective.singing.message.Message(
            message, subscription, status=None)

def plone_html_strip(html):
    r"""
      >>> html = (
      ...     '<html><body><h1 class="documentFirstHeading">'
      ...     'Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
      ...     '<div class="visualClear"></div></body></html>')
      >>> plone_html_strip(html)
      u'<h1 class="documentFirstHeading">Hi, it\'s me!</h1><p>Wannabe the son of Frankenstein</p>'
    """
    if not isinstance(html, unicode):
        html = unicode(html, 'UTF-8')

    first_index = html.find('<h1 class="documentFirstHeading">')
    second_index = html.find('<div class="visualClear"', first_index)
    return html[first_index:second_index]

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
        html = self.item()
        if 'kss' in html:
            return plone_html_strip(html)
        else:
            return html

class FullFormatWrapper(object):
    """Wraps an item for use with a full formatter."""
    
    def __init__(self, item):
        self.item = item

class HTMLFormatItemFully(object):
    interface.implements(collective.singing.interfaces.IFormatItem)
    component.adapts(FullFormatWrapper, zope.publisher.interfaces.browser.IBrowserRequest)
    
    def __init__(self, wrapper, request):
        self.item = wrapper.item
        self.request = request
                 
    def __call__(self):
        view = component.getMultiAdapter(
            (self.item, self.request), IFullFormatter, name='html')

        return view()

class SMTPMailer(object):
    """A mailer for use with zope.sendmail that fetches settings from
    the Plone site's configuration.
    """
    interface.implements(zope.sendmail.interfaces.ISMTPMailer)

    SMTP = smtplib.SMTP

    def _fetch_settings(self):
        root = component.getUtility(Products.CMFPlone.interfaces.IPloneSiteRoot)
        m = root.MailHost
        return dict(hostname=m.smtp_host or 'localhost',
                    port=m.smtp_port,
                    username=m.smtp_userid or m.smtp_uid or None,
                    password=m.smtp_pass or m.smtp_pwd or None,)

    def send(self, fromaddr, toaddrs, message):
        cfg = self._fetch_settings()

        connection = self.SMTP(cfg['hostname'], str(cfg['port']))
        if cfg['username'] is not None and cfg['password'] is not None:
            connection.login(cfg['username'], cfg['password'])
        connection.sendmail(fromaddr, toaddrs, message)
        connection.quit()
