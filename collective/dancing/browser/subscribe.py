import datetime

from zope import component
from zope.app.component.hooks import getSite
from zope.app.pagetemplate import viewpagetemplatefile
import zope.i18n.interfaces
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from z3c.form import button
from z3c.form import field
from z3c.form import form
from plone.z3cform import z2
import collective.singing.interfaces
import collective.singing.message
import collective.singing.browser.subscribe
from collective.singing.channel import channel_lookup
from collective.dancing import MessageFactory as _

class SubscribeForm(collective.singing.browser.subscribe.Subscribe):
    already_subscribed_message = _(
        u'Your email address is already subscribed. Click the '
        '"Send my subscription details" button below.')

class SendSecret(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents_template = ViewPageTemplateFile('sendsecret.pt')

    label = _(u"Edit existing subscriptions")

    description = _(
        u"Fill out the form below to receive an email with a link from which "
        "you can edit your subscriptions.")

    def forgot_secret_form(self):
        form = collective.singing.browser.subscribe.ForgotSecret(
            self.context, self.request)
        form.label = u''
        return form()

    def __call__(self):
        z2.switch_on(self)
        return self.template()

    def contents(self):
        return self.contents_template()

class Subscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents_template = ViewPageTemplateFile('subscribe.pt')

    @property
    def send_secret_link(self):
        return _(
            u'Fill out the form below to subscribe to ${channel}. Note that '
            'this is for new subscriptions. Click here to '
            '<a href="${url}">edit your subscriptions</a>.',
            mapping={'channel': self.context.Title(),
                     'url': '%s/portal_newsletters/sendsecret.html' % getSite().absolute_url()})
    
    @property
    def label(self):
        return _(u"Subscribe to ${channel}",
                 mapping={'channel': self.context.Title()})

    def __call__(self):
        z2.switch_on(self,
                     request_layer=collective.singing.interfaces.IFormLayer)
        return self.template()

    def contents(self):
        self.subscribeform = SubscribeForm(self.context.aq_inner, self.request)
        return self.contents_template()


class Confirm(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Confirming your subscription")

    successMessage = _(u"You confirmed your subscription successfully.")
    notKnownMessage = _(u"Your subscription isn't known to us.")

    def __call__(self):
        secret = self.request.form['secret']
        exists = False

        for channel in channel_lookup(only_subscribeable=True):
            subscriptions = channel.subscriptions.query(secret=secret)
            if len(subscriptions):
                exists = True
                for sub in subscriptions:
                    if sub.metadata.get('pending', False):
                        sub.metadata['pending'] = False

        if exists:
            self.status = self.successMessage
        else:
            self.status = self.notKnownMessage

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
        secret = self.secret
        if secret is not None:
            index = html.find('</form>')
            html = (html[:index] +
                    '<input type="hidden" name="secret" value="%s"' % secret +
                    html[index:])
        return html

    @property
    def secret(self):
        secret = self.request.form.get('secret')
        if isinstance(secret, list):
            return secret[0]
        return secret

class SubscriptionEditForm(IncludeHiddenSecret, form.EditForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')    
    successMessage = _('Your subscription was updated.')
    removed = False
    handlers = form.EditForm.handlers

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

    def update(self):
        if len(self.fields) == 0:
            self.buttons = self.buttons.omit('apply')
        super(SubscriptionEditForm, self).update()

    @button.buttonAndHandler(_('Apply changes'), name='apply')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changes = self.applyChanges(data)
        if changes:
            self.status = self.successMessage
        else:
            self.status = self.noChangesMessage

    @button.buttonAndHandler(_('Unsubscribe from newsletter'), name='unsubscribe')
    def handle_unsubscribe(self, action):
        secret = self.secret
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
    status_already_subscribed = _(u"You are already subscribed. Fill out the form at the end of this page to be sent a link from where you can edit your subscription.")
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
        if self.context.collector is not None:
            fields = field.Fields(self.context.collector.schema,
                                   prefix='collector.')
        else:
            fields = field.Fields()
        fields += field.Fields(self.context.composers[self.format].schema,
                               prefix='composer.')
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
        secret_provided = self.secret
        if secret_provided and secret != secret_provided:
            self.status = _(
                u"There seems to be an error with the information you entered.")
            return

        metadata = dict(
            format=self.format,
            date=datetime.datetime.now(),
            pending=not secret_provided)

        # We assume here that the language of the request is the
        # desired language of the subscription:
        pl = component.queryAdapter(
            self.request, zope.i18n.interfaces.IUserPreferredLanguages)
        if pl is not None:
            metadata['languages'] = pl.getPreferredLanguages()

        # By using another method here we allow subclasses to override
        # what really happens here:
        self.add_subscription(
            self.context, secret, comp_data, coll_data, metadata,
            secret_provided)

    def add_subscription(self, context, secret, comp_data, coll_data, metadata,
                         secret_provided):
        try:
            self.added = self.context.subscriptions.add_subscription(
                self.context, secret, comp_data, coll_data, metadata)
        except ValueError, e:
            self.added = None
            self.status = self.status_already_subscribed
            return
            
        self.status = _(u"You subscribed successfully.")
        if not secret_provided:
            composer = self.context.composers[self.format]
            msg = composer.render_confirmation(self.added)
            status, status_msg = collective.singing.message.dispatch(msg)
            if status == u'sent':
                self.status = _(u"Information on how to confirm your "
                                "subscription has been sent to you.")
            else:
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
    def addforms(self):
        return [f for f in self.subscription_addforms if not f.added]

    @property
    def editforms(self):
        return [f for f in self.subscription_editforms if not f.removed]

    @property
    def secret(self):
        secret = self.request.form.get('secret')
        if isinstance(secret, list):
            return secret[0]
        return secret

    def contents(self):
        z2.switch_on(self,
                     request_layer=collective.singing.interfaces.IFormLayer)

        subscriptions, channels = self._subscriptions_and_channels(self.secret)

        # Let's set convert any 'pending' subscriptions to non-pending:
        for sub in subscriptions:
            if sub.metadata.get('pending'):
                sub.metadata['pending'] = False

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
                addform.status = form.status
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
                editform.status = form.status#_(u"You subscribed successfully.")

        return self.contents_template()

    def _subscriptions_and_channels(self, secret):
        subscriptions = []
        channels_and_formats = []

        for channel in channel_lookup(only_subscribeable=True):
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
