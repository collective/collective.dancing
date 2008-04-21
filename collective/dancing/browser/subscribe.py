import datetime

from zope import component
from zope.app.pagetemplate import viewpagetemplatefile
import Acquisition
import Zope2.App.startup
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form import button
from z3c.form import field
from z3c.form import form
from plone.z3cform import z2
import collective.singing.interfaces
import collective.singing.message
import collective.singing.browser.subscribe

from collective.dancing import MessageFactory as _

class SubscribeForm(collective.singing.browser.subscribe.Subscribe):
    pass

class Subscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    label = _(u"Subscribe")

    def __call__(self):
        z2.switch_on(self)
        return self.template()

    def contents(self):
        subscribe = SubscribeForm(self.context.aq_inner, self.request)
        return subscribe()

class Confirm(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Confirming your subscription")

    def __call__(self):
        secret = self.request.form['secret']
        query = self.context.aq_inner.subscriptions.query

        subscriptions = query(secret=secret)
        if len(subscriptions):
            for sub in subscriptions:
                sub.metadata['pending'] = False
            self.status = _(u"You confirmed your subscription successfully.")
        else:
            self.status = _(u"Your subscription isn't known to us.")

        return self.template()

class Unsubscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Unsubscribe")

    def __call__(self):
        secret = self.request.form['secret']
        subs = self.context.aq_inner.subscriptions
        
        subscriptions = subs.query(secret=secret)
        if len(subscriptions):
            for sub in subscriptions:
                subs.remove_subscription(sub)
            self.status = _(u"You unsubscribed successfully.")
        else:
            self.status = _(u"You aren't subscribed to this channel.")

        return self.template()

class IncludeHiddenSecret(object):
    def render(self):
        html = super(IncludeHiddenSecret, self).render()
        secret = self.request.get('secret')
        if secret is not None:
            index = html.find('</form>')
            html = (html[:index] +
                    '<input type="hidden" name="secret" value="%s"' % secret +
                    html[index:])
        return html

class SubscriptionEditForm(IncludeHiddenSecret, form.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')    

    removed = False

    @property
    def description(self):
        return self.context.channel.description

    @property
    def prefix(self):
        return '%s.%s.' % (
            self.context.channel.name, self.context.metadata['format'])

    @property
    def label(self):
        subscription = self.context
        value = subscription.channel.title
        if len(subscription.channel.composers) > 1:
            format = subscription.metadata['format']
            value = u"%s (%s)" % (
                value, subscription.channel.composers[format].title)
        return value

    @property
    def fields(self):
        if self.context.channel.collector is None:
            return field.Fields()
        return field.Fields(self.context.channel.collector.schema)

    buttons, handlers = form.EditForm.buttons, form.EditForm.handlers
    
    @button.buttonAndHandler(_('Unsubscribe'), name='unsubscribe')
    def handle_unsubscribe(self, action):
        secret = self.request.form['secret']
        subs = self.context.channel.subscriptions
        for subscription in subs.query(secret=secret):
            subs.remove_subscription(subscription)
        self.removed = self.context
        self.status = _(u"You unsubscribed successfully.")

class SubscriptionAddForm(IncludeHiddenSecret, form.Form):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    ignoreContext = True
    
    added = None
    format = None # set by parent form

    @property
    def description(self):
        return self.context.description
        
    @property
    def prefix(self):
        return '%s.%s.' % (self.context.name, self.format)

    @property
    def label(self):
        value = self.context.title
        if len(self.context.composers) > 1:
            value = u"%s (%s)" % (
                value, self.context.composers[self.format].title)
        return value

    @property
    def fields(self):
        fields = field.Fields(self.context.composers[self.format].schema,
                              prefix='composer.')
        if self.context.collector is not None:
            fields += field.Fields(self.context.collector.schema,
                                   prefix='collector.')
        return fields

    @button.buttonAndHandler(_('Subscribe'), name='subscribe')
    def handle_subscribe(self, action):
        data, errors = self.extractData()
        
        if errors:
            self.status = form.AddForm.formErrorsMessage
            return

        extract = lambda d, prefix: dict(
            [(key.split('.', 1)[-1], value) for (key, value) in d.items()
             if key.startswith(prefix)])

        comp_data = extract(data, 'composer.')
        coll_data = extract(data, 'collector.')

        composer = self.context.composers[self.format]
        secret = collective.singing.subscribe.secret(
            self.context,
            composer,
            comp_data,
            self.request)
        secret_provided = self.request.form.get('secret')
        if secret_provided and secret != secret_provided:
            self.status = _(
                u"There seems to be an error with the information you entered.")
            return

        metadata = dict(
            format=self.format,
            date=datetime.datetime.now(),
            pending=not secret_provided)

        try:
            self.added = self.context.subscriptions.add_subscription(
                self.context, secret, comp_data, coll_data, metadata)
        except ValueError:
            self.added = None
            self.status = _(u"You are already subscribed.")
            return

        self.status = _(u"You subscribed successfully.")
        if not secret_provided:
            msg = composer.render_confirmation(self.added)
            status, status_msg = collective.singing.message.dispatch(msg)
            if status != u'sent':
                # This implicitely rolls back our transaction.
                raise RuntimeError(
                    "There was an error with sending your e-mail.  Please try "
                    "again later.")


class Subscriptions(BrowserView):
    __call__ = ViewPageTemplateFile('skeleton.pt')
    contents_template = ViewPageTemplateFile('subscriptions.pt')

    label = _(u"My subscriptions")
    status = u""

    def forgot_secret_form(self):
        form = collective.singing.browser.subscribe.ForgotSecret(
            self.context, self.request)
        form.label = u''
        return form()

    @property
    def secret(self):
        return self.request.form.get('secret')

    def contents(self):
        z2.switch_on(self)

        subscriptions, channels = self._subscriptions_and_channels(self.secret)

        # Assemble the list of edit forms
        self.subscription_editforms = [
            SubscriptionEditForm(s, self.request) for s in subscriptions]

        # Assemble the list of add forms
        self.subscription_addforms = []
        for format, channel in channels:
            addform = SubscriptionAddForm(channel, self.request)
            addform.format = format
            self.subscription_addforms.append(addform)

        # The edit forms might have deleted a subscription.  We'll
        # take care of this while updating them:
        for form in self.subscription_editforms:
            form.update()
            if form.removed:
                subscription = form.context
                name = subscription.channel.name
                addform = SubscriptionAddForm(
                    subscription.channel, self.request)
                addform.format = subscription.metadata['format']
                addform.update()
                self.subscription_addforms.append(addform)
            elif form.status != form.noChangesMessage:
                self.status = form.status

        # Let's update the add forms now.  One of them may have added
        # a subscription:
        for form in self.subscription_addforms:
            form.update()
            subscription = form.added
            if subscription is not None:
                editform = SubscriptionEditForm(
                    subscription, self.request)
                editform.update()
                self.subscription_editforms.append(editform)
                self.status = _(u"You subscribed successfully.")
            elif form.status:
                self.status = form.status

        return self.contents_template()

    def _subscriptions_and_channels(self, secret):
        subscriptions = []
        channels_and_formats = []

        for channel in component.getUtility(
            collective.singing.interfaces.IChannelLookup)():
            channel_subs = channel.subscriptions

            subscribed_formats = []
            if self.secret is not None:
                for s in channel_subs.query(secret=self.secret):
                    subscriptions.append(s)
                    subscribed_formats.append(s.metadata['format'])

            for format in channel.composers.keys():
                if format not in subscribed_formats:
                    channels_and_formats.append((format, channel))

        return subscriptions, channels_and_formats
