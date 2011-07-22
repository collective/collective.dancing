import datetime
import operator

from zope import component
from zope import schema
from zope.app.component.hooks import getSite
from zope.app.pagetemplate import viewpagetemplatefile
import zope.i18n.interfaces
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from zExceptions import BadRequest
from z3c.form import button
from z3c.form import field
from z3c.form import form
from z3c.form import subform
import z3c.form.interfaces
import z3c.form
from plone.z3cform import z2
from plone.z3cform.widget import singlecheckboxwidget_factory
import collective.singing.interfaces
import collective.singing.message
import collective.singing.browser.subscribe
from collective.singing.channel import channel_lookup

from collective.dancing import MessageFactory as _
from collective.dancing.utils import switch_on


class SubscribeForm(collective.singing.browser.subscribe.Subscribe):
    already_subscribed_message = _(
        u"Your email address is already subscribed. Click the "
        "'Send my subscription details' button below.")

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
        switch_on(self)
        return self.template()

    def contents(self):
        return self.contents_template()

class Subscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents_template = ViewPageTemplateFile('subscribe.pt')

    @property
    def send_secret_link(self):
        link_start = '<a href="%s/portal_newsletters/sendsecret.html">' % (
            getSite().absolute_url())
        link_end = '</a>'
        # The link_start plus link_end construction is not very
        # pretty, but it is needed to avoid syntax errors in the
        # generated po files.
        return _(
            u'Fill out the form below to subscribe to ${channel}. Note that '
            'this is for new subscriptions. Click here to '
            '${link_start}edit your subscriptions${link_end}.',
            mapping={'channel': self.context.Title(),
                     'link_start': link_start,
                     'link_end': link_end})

    @property
    def label(self):
        return _(u"Subscribe to ${channel}",
                 mapping={'channel': self.context.Title()})

    def __call__(self):
        switch_on(self,
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

        if secret:
            for channel in channel_lookup(only_subscribeable=True):
                subscriptions = channel.subscriptions.query(secret=secret)
                if len(subscriptions):
                    for sub in subscriptions:
                        if sub.metadata.get('pending', False):
                            sub.metadata['pending'] = False
                    self.status = self.successMessage
                    break
            else:
                self.status = self.notKnownMessage
        else:
            self.status = _(u"Can't identify your subscription. "
                            u"Please check your URL.")

        return self.template()

class Unsubscribe(BrowserView):
    template = ViewPageTemplateFile('skeleton.pt')
    contents = ViewPageTemplateFile('status.pt')

    label = _(u"Unsubscribe")

    def __call__(self):
        secret = self.request.form['secret']
        if secret:
            subs = self.context.aq_inner.subscriptions
            subscriptions = subs.query(secret=secret)

            if len(subscriptions):
                for sub in subscriptions:
                    subs.remove_subscription(sub)
                self.status = _(u"You unsubscribed successfully.")
            else:
                self.status = _(u"You aren't subscribed to this mailing-list.")
        else:
            self.status = _(u"Can't identify your subscription. "
                            u"Please check your URL.")

        return self.template()

class IncludeHiddenSecret(object):
    def render(self):
        html = super(IncludeHiddenSecret, self).render()
        secret = self.secret
        if secret is not None:
            index = html.find('</form>')
            html = (html[:index] +
                    '<input type="hidden" name="secret" value="%s" />' % (
                    secret) +
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
        except ValueError:
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


class SubscriptionSubForm(IncludeHiddenSecret, subform.EditSubForm):
    status_already_subscribed = _(u"You are already subscribed. "
                                  "Fill out the form at the end of this "
                                  "page to be sent a link from where you "
                                  "can edit your subscription.")
    status_error = _(u"There seems to be an error with the "
                     "information you entered.")
    status_sent = _(u"Information on how to confirm your "
                    "subscription has been sent to you.")
    successMessage = _('Your subscription was updated.')
    status_subscribed = _(u"You subscribed successfully.")
    status_unsubscribed = _(u"You unsubscribed successfully.")

    def update(self):
        super(SubscriptionSubForm, self).update()
        # set label on channel-checkbox
        # indent other widgets
        widgets = self.widgets.values()
        widgets[0].items[0]['label'] = self.label
        widgets[0].label = u''
        for widget in widgets[1:]:
            #widget.label = u""
            #widget.required = False
            widget.addClass('level-1')


class SubscriptionAddSubForm(SubscriptionSubForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')

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
    def channel_selector(self):
        return '%s-%s' % (self.context.name,
                          self.format)

    @property
    def fields(self):
        if self.context.collector is not None:
            fields = field.Fields(self.context.collector.schema,
                                   prefix='collector.')
        else:
            fields = field.Fields()

        comp_fields = field.Fields(self.context.composers[self.format].schema,
                                   prefix='composer.')
        fields += comp_fields.omit(
            *['composer.'+f.getName() for f in self.parentForm.key_fields])

        select_field = field.Field(
            schema.Bool(
            __name__=self.channel_selector,
            title=self.label,
            default=False,
            required=False,
            ))
        select_field.widgetFactory[z3c.form.interfaces.INPUT_MODE] = (
            singlecheckboxwidget_factory)

        return field.Fields(select_field, prefix='selector.') + fields

    def update(self):
        def handleApply(self, action):
            data, errors = self.extractData()

            if not data.get(self.channel_selector):
                return

            if errors:
                self.status = form.AddForm.formErrorsMessage
                return

            extract = lambda d, prefix: dict(
                [(key.split('.', 1)[-1], value) for (key, value) in d.items()
                 if key.startswith(prefix)])

            comp_data = extract(data, 'composer.')
            coll_data = extract(data, 'collector.')

            pdata, perrors = self.parentForm.extractData()
            comp_data.update(pdata)

            composer = self.context.composers[self.format]
            secret = collective.singing.subscribe.secret(
                self.context,
                composer,
                comp_data,
                self.request)
            secret_provided = self.secret
            if secret_provided and secret != secret_provided:
                self.status = self.status_error
                return

            # Check if subscribed to other channels
            if not secret_provided and not self.parentForm.confirmation_sent:
                existing = sum(
                    [len(channel.subscriptions.query(secret=secret)) \
                     for channel in channel_lookup(only_subscribeable=True)])
                if existing:
                    self.status = self.status_already_subscribed
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

        self.handlers = button.Handlers()
        self.handlers.addHandler(
            self.parentForm.buttons['apply'], handleApply)

        super(SubscriptionAddSubForm, self).update()


    def add_subscription(self, context, secret, comp_data, coll_data, metadata,
                         secret_provided):
        try:
            self.added = self.context.subscriptions.add_subscription(
                self.context, secret, comp_data, coll_data, metadata)
        except ValueError:
            self.added = None
            self.status = self.status_already_subscribed
            return

        self.status = self.status_subscribed

        if not secret_provided:
            self.parentForm.send_confirmation(self.context, self.format, self.added)

class SubscriptionEditSubForm(SubscriptionSubForm):
    template = viewpagetemplatefile.ViewPageTemplateFile('subform.pt')
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
    def channel_selector(self):
        return '%s-%s' % (self.context.channel.name,
                          self.context.metadata['format'])

    @property
    def fields(self):
        select_field = field.Field(
            schema.Bool(
            __name__=self.channel_selector,
            title=self.label,
            default=True,
            required=False
            ))
        select_field.widgetFactory[z3c.form.interfaces.INPUT_MODE] = (
            singlecheckboxwidget_factory)

        fields = field.Fields(select_field, prefix='selector.')

        if self.context.channel.collector is not None:
            fields += field.Fields(
                self.context.channel.collector.schema,
                prefix='collector.')
        return fields

    def update(self):
        def handleApply(self, action):
            data, errors = self.extractData()

            if not data.get(self.channel_selector):
                self.unsubscribe()
                return
            if errors:
                self.status = self.formErrorsMessage
                return

            content = self.getContent()
            del data[self.channel_selector]

            changes = form.applyChanges(self, content, data)
            if changes:
                zope.event.notify(
                    zope.lifecycleevent.ObjectModifiedEvent(content))
                self.status = self.successMessage
            else:
                self.status = self.noChangesMessage

        self.handlers = button.Handlers()
        self.handlers.addHandler(
            self.parentForm.buttons['apply'], handleApply)

        super(SubscriptionEditSubForm, self).update()


    def unsubscribe(self):
        secret = self.secret
        format = self.context.metadata['format']
        subs = self.context.channel.subscriptions
        for subscription in subs.query(secret=secret, format=format):
            subs.remove_subscription(subscription)
        self.removed = self.context
        self.status = self.status_unsubscribed

class PrettySubscriptionsForm(IncludeHiddenSecret, form.EditForm):

    template = viewpagetemplatefile.ViewPageTemplateFile(
        'prettysubscriptionsform.pt')
    ignoreContext = True
    ignoreRequest = True
    confirmation_sent = False
    status_message = None

    def __init__(self, context, request, subs, channels):
        super(PrettySubscriptionsForm, self).__init__(context, request)
        self.subs = subs
        self.channels = channels
        self.key_fields = []
        channels = channel_lookup(only_subscribeable=True)
        if channels:
            composers = reduce(
                lambda x,y:x+y,
                [c.composers.values() for c in channels])
            for composer in composers:
                for name in composer.schema.names():
                    f = composer.schema.get(name)
                    if f and \
                           collective.singing.interfaces.ISubscriptionKey.providedBy(f):
                        if f not in self.key_fields:
                            self.key_fields.append(f)
        self.confirmation_sent = False

    def status(self):
        if self.status_message:
            return self.status_message
        stati = [form.status for form in self.forms]

        for s in [SubscriptionSubForm.status_already_subscribed,
                  SubscriptionSubForm.status_sent,
                  SubscriptionSubForm.successMessage]:
            if s in stati:
                return s

        for s in [SubscriptionSubForm.status_subscribed,
                  SubscriptionSubForm.status_unsubscribed]:
            if s in stati:
                return SubscriptionSubForm.successMessage

        return ''

    @property
    def addforms(self):
        return [f for f in self.subscription_addforms if not f.added]

    @property
    def editforms(self):
        return [f for f in self.subscription_editforms if not f.removed]

    @property
    def forms(self):
        return sorted(
            self.addforms + self.editforms,
            key=operator.attrgetter('label'))

    @property
    def fields(self):
        fields = field.Fields()
        for kf in self.key_fields:
            f = field.Field(kf)
            if self.subs:
                kf.default = self.subs[0].composer_data[kf.getName()]
            fields += field.Fields(f)
        return fields

    def update(self):
        super(PrettySubscriptionsForm, self).update()

        if self.subs: #existing subscriptions
            for f_name in [f.getName() for f in self.key_fields]:
                # FIXME: widget is never used in this code!
                widget = self.widgets.get(f_name)

        # Let's set convert any 'pending' subscriptions to non-pending:
        for sub in self.subs:
            if sub.metadata.get('pending'):
                sub.metadata['pending'] = False

        # Assemble the list of edit forms
        self.subscription_editforms = [
            SubscriptionEditSubForm(s, self.request, self) for s in self.subs]

        # Assemble the list of add forms
        self.subscription_addforms = []
        for format, channel in self.channels:
            addform = SubscriptionAddSubForm(channel, self.request, self)
            addform.format = format
            self.subscription_addforms.append(addform)

        # The edit forms might have deleted a subscription.  We'll
        # take care of this while updating them:
        for form in self.subscription_editforms:
            form.update()
            if form.removed:
                subscription = form.context
                addform = SubscriptionAddSubForm(
                    subscription.channel, self.request, self)
                addform.format = subscription.metadata['format']
                addform.ignoreRequest = True
                addform.update()
                self.subscription_addforms.append(addform)
                addform.status = form.status
            #elif form.status != form.noChangesMessage:
            #    self.status = form.status

        # Let's update the add forms now.  One of them may have added
        # a subscription:
        for form in self.subscription_addforms:
            form.update()
            subscription = form.added
            if subscription is not None:
                editform = SubscriptionEditSubForm(
                    subscription, self.request, self)
                editform.update()
                self.subscription_editforms.append(editform)
                editform.status = form.status#_(u"You subscribed successfully.")

    @button.buttonAndHandler(_('Apply'), name='apply')
    def handle_apply(self, action):
        # All the action happens in the subforms ;-)
        # All we do here is check that key_fields were not altered
        if self.subs:
            data, errors = self.extractData()
            key_defaults = dict(
                [(f.getName(), f.default) for f in self.key_fields])
            for key, value in data.items():
                if key_defaults[key] != value:
                    self.status_message = SubscriptionSubForm.status_error

    def send_confirmation(self, channel, format, subscription):
        if not self.confirmation_sent:
            composer = channel.composers[format]
            msg = composer.render_confirmation(subscription)
            status, status_msg = collective.singing.message.dispatch(msg)
            if status == u'sent':
                self.status_message = _(u"Information on how to confirm your "
                                        "subscription has been sent to you.")
                self.confirmation_sent = True
            else:
                # This implicitely rolls back our transaction.
                raise RuntimeError(
                    "There was an error with sending your e-mail.  Please try "
                    "again later.")

class Subscriptions(BrowserView):
    __call__ = ViewPageTemplateFile('skeleton.pt')
    contents_template = ViewPageTemplateFile('subscriptions.pt')
    single_form_template = ViewPageTemplateFile('prettysubscriptions.pt')

    label = _(u"My subscriptions")
    status = u""

    def forgot_secret_form(self):
        form = collective.singing.browser.subscribe.ForgotSecret(
            self.context, self.request)
        form.label = u''
        return form()

    @property
    def newsletters(self):
        return getSite().portal_newsletters

    @property
    def single_form_subscriptions(self):
        return self.newsletters.get('use_single_form_subscriptions_page', '')

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
        switch_on(self,
                  request_layer=collective.singing.interfaces.IFormLayer)
        subscriptions, channels = self._subscriptions_and_channels(self.secret)

        if self.single_form_subscriptions:
            self.form = PrettySubscriptionsForm(self.context, self.request,
                                                subscriptions, channels)
            self.form.update()
            if len(self.form.key_fields) == 1:
                # Revert to old style form if not all
                # composers have the same ISubscriptionKey.
                return self.single_form_template()

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


#############
from zope.schema.vocabulary import SimpleVocabulary
from collective.dancing.composer import HTMLComposer

class MyHTMLComposer(HTMLComposer):
    title = u'Hypertext E-Mail with selectable font-size'
    class schema(HTMLComposer.schema):
        font_size = schema.Choice(
            title=u"Font size",
            vocabulary=SimpleVocabulary.fromValues([8, 12, 16]))
