import md5
import re

from zope import interface
from zope import component
from zope import schema
import zope.annotation.interfaces
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
import zope.app.component.hooks
import Products.CMFCore.interfaces
import collective.singing.interfaces
import collective.singing.mail

from collective.dancing import MessageFactory as _

class AttributeToDictProxy(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped

    def __setitem__(self, name, value):
        self.wrapped[name] = value

    def __getattr__(self, name):
        return self.wrapped[name]

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
    return AttributeToDictProxy(composer_data)

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
