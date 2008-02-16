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
import Products.CMFCore.interfaces
import Products.CMFPlone.interfaces
import collective.singing.interfaces
import collective.singing.mail

from collective.dancing import MessageFactory as _
from collective.dancing import utils

class InvalidEmailAddress(schema.ValidationError):
    _(u"Your e-mail address is invalid")
    regex = r"[a-zA-Z0-9._%-]+@([a-zA-Z0-9-]+\.)*[a-zA-Z]{2,4}"

def check_email(value):
    if not re.match(InvalidEmailAddress.regex, value):
        raise InvalidEmailAddress
    return True

class IHTMLComposerSchema(interface.Interface):
    email = schema.TextLine(title=_(u"E-mail address"),
                            constraint=check_email)

@component.adapter(collective.singing.interfaces.ISubscription)
@interface.implementer(IHTMLComposerSchema)
def composerdata_from_subscription(subscription):
    composer_data = collective.singing.interfaces.IComposerData(subscription)
    return utils.AttributeToDictProxy(composer_data)

class HTMLComposer(object):
    interface.implements(collective.singing.interfaces.IComposer,
                         collective.singing.interfaces.IComposerBasedSecret)

    title = _(u'HTML E-Mail')
    schema = IHTMLComposerSchema

    template = ViewPageTemplateFile('browser/composer-html.pt')
    confirm_template = ViewPageTemplateFile('browser/composer-html-confirm.pt')

    @staticmethod
    def secret(data):
        return md5.new(data['email'] + 'XXX').hexdigest()
    
    context = None
    @property
    def request(self):
        site = zope.app.component.hooks.getSite()
        return site.REQUEST

    @property
    def _from_address(self):
        properties = component.getUtility(
            Products.CMFCore.interfaces.IPropertiesTool)
        return collective.singing.mail.header(
            '%s <%s>' %
            (properties.email_from_name, properties.email_from_address),
            encoding='UTF-8')

    def _render_html(self, subscription, items, subject):
        composer_data = collective.singing.interfaces.IComposerData(
            subscription)
        channel = subscription.channel
        secret = self.secret(composer_data)
        
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

        composer_data = collective.singing.interfaces.IComposerData(
            subscription)
        message = collective.singing.mail.create_html_mail(
            subject,
            html,
            from_addr=self._from_address,
            to_addr=composer_data['email'])

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

        composer_data = collective.singing.interfaces.IComposerData(
            subscription)
        message = collective.singing.mail.create_html_mail(
            subject,
            html.encode('UTF-8'),
            from_addr=self._from_address,
            to_addr=composer_data['email'])

        return collective.singing.message.Message(
            message, subscription)

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

class HTMLFormatter(object):
    """Format HTML for callable items.
    """
    interface.implements(collective.singing.interfaces.IFormatItem)

    def __init__(self, item):
        self.item = item

    def __call__(self):
        html = self.item()
        return plone_html_strip(html)

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
