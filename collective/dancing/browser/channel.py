import types
import cStringIO
import datetime
import sys
import sets
import csv
from zope import interface
from zope import component
from zope import schema
import zope.interface
import zope.schema.interfaces
import zope.schema.vocabulary
import zope.i18n
from z3c.form import field, form
import z3c.form.interfaces
import z3c.form.datamanager
import z3c.form.term
import z3c.form.button
import OFS.SimpleItem
from Globals import DevelopmentMode
from Products.Five import BrowserView
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile
from Products.CMFCore.interfaces import IPropertiesTool
from Acquisition import aq_inner
import Products.CMFPlone.utils
from collective.singing.interfaces import IChannel, ICollectorSchema
from plone.z3cform.crud import crud
from plone.app.z3cform import wysiwyg
import collective.singing.scheduler
import collective.singing.subscribe
import collective.singing.channel
from zope.app.pagetemplate import viewpagetemplatefile
from collective.dancing import MessageFactory as _
from collective.dancing import utils
from collective.dancing import channel
from collective.dancing.composer import check_email
from collective.dancing.browser import controlpanel
from collective.dancing.browser.interfaces import ISendAndPreviewForm
from collective.dancing.utils import switch_on


def simpleitem_wrap(klass, name):
    class SimpleItemWrapper(klass, OFS.SimpleItem.SimpleItem):
        __doc__ = OFS.SimpleItem.SimpleItem.__doc__
        id = name
        def Title(self):
            return klass.title

    klassname = klass.__name__
    SimpleItemWrapper.__name__ = klassname
    module = sys.modules[__name__]
    assert not hasattr (module, klassname), "%r already a name in this module."
    setattr(module, klassname, SimpleItemWrapper)
    return SimpleItemWrapper

schedulers = [
    simpleitem_wrap(klass, 'scheduler')
    for klass in collective.singing.scheduler.schedulers]

csv_delimiter = ","

class FactoryChoice(schema.Choice):
    def _validate(self, value):
        if self._init_field:
            return
        super(schema.Choice, self)._validate(value)

        # We'll skip validating against the vocabulary

def scheduler_vocabulary(context):
    terms = []
    for factory in schedulers:
        terms.append(
            zope.schema.vocabulary.SimpleTerm(
                value=factory(),
                token='%s.%s' % (factory.__module__, factory.__name__),
                title=factory.title))
    return utils.LaxVocabulary(terms)
zope.interface.alsoProvides(scheduler_vocabulary,
                            zope.schema.interfaces.IVocabularyFactory)

class ChannelEditForm(crud.EditForm):
    def _update_subforms(self):
        self.subforms = []
        for channel in collective.singing.channel.channel_lookup():
            subform = crud.EditSubForm(self, self.request)
            subform.content = channel
            subform.content_id = channel.name
            subform.update()
            self.subforms.append(subform)

class ManageChannelsForm(crud.CrudForm):
    """Crud form for channels."""

    description = _("Add or edit mailing-lists that will use collectors to "
                    "gather and email specific sets of information from "
                    "your site, to subscribed email addresses, at scheduled "
                    "times.")

    editform_factory = ChannelEditForm

    @property
    def add_schema(self):
        if len(channel.channels) > 1:
            return self.update_schema + field.Fields(
                schema.Choice(
                __name__='factory',
                title=_(u"Type"),
                vocabulary=zope.schema.vocabulary.SimpleVocabulary(
                    [zope.schema.vocabulary.SimpleTerm(value=c, title=c.type_name)
                     for c in channel.channels])
                ))
        return self.update_schema

    @property
    def update_schema(self):
        fields = field.Fields(IChannel).select('title')

        collector = schema.Choice(
            __name__='collector',
            title=IChannel['collector'].title,
            required=False,
            vocabulary='Collector Vocabulary')

        scheduler = FactoryChoice(
            __name__='scheduler',
            title=IChannel['scheduler'].title,
            required=False,
            vocabulary='Scheduler Vocabulary')

        fields += field.Fields(collector, scheduler)

        fields += field.Fields(IChannel).select('subscribeable')

        return fields

    @property
    def view_schema(self):
        return self.update_schema.copy()

    def get_items(self):
        return collective.singing.channel.channel_lookup()

    def add(self, data):
        name = Products.CMFPlone.utils.normalizeString(
            data['title'].encode('utf-8'), encoding='utf-8')
        factory = data.get('factory', None) or channel.channels[0]
        self.context[name] = factory(
            name, data['title'],
            collector=data['collector'],
            scheduler=data['scheduler'])
        return self.context[name]

    def remove(self, (id, item)):
        self.context.manage_delObjects([id])

    def link(self, item, field):
        if field == 'title':
            return item.absolute_url()
        elif field == 'collector' and item.collector is not None:
            collector_id = item.collector.getId()
            collector = getattr(self.context.aq_inner.aq_parent.collectors,
                                collector_id)
            return collector.absolute_url()
        elif field == 'scheduler':
            if item.scheduler is not None:
                return item.scheduler.absolute_url()


class ChannelAdministrationView(BrowserView):
    __call__ = ViewPageTemplateFile('controlpanel.pt')

    label = _(u"label_channel_administration",
              default="Mailing-list administration")
    back_link = controlpanel.back_to_controlpanel

    def contents(self):
        switch_on(self)
        return ManageChannelsForm(self.context.channels, self.request)()

class SubscriptionsSearchForm(z3c.form.form.Form):
    prefix = 'search.'
    ignoreContext = True

    fields = field.Fields(
        schema.TextLine(
        __name__='fulltext',
        title=_(u"Search subscribers"),
        ))

    @z3c.form.button.buttonAndHandler(_('Search'), name='search')
    def handle_search(self, action):
        pass

class ManageSubscriptionsFormEdit(crud.EditForm):
    def update(self):
        super(ManageSubscriptionsFormEdit, self).update()
        self.search = SubscriptionsSearchForm(self.context, self.request)
        self.search.update()

    def render(self):
        table = super(ManageSubscriptionsFormEdit, self).render()
        name = self.search.widgets['fulltext'].name
        search = self.request.form.get(name)
        if search and table.strip():
            idx = table.find('</form>')
            hidden = ('<input type="hidden" name="%s" value="%s" />' %
                      (name, search))
            table = table[:idx] + hidden + table[idx:]
        return ('<div id="subscriber-search">%s</div>' % self.search.render() +
                table)

class ManageSubscriptionsForm(crud.CrudForm):
    """Crud form for subscriptions.
    """
    # These are set by the SubscriptionsAdministrationView
    format = None
    composer = None

    description = _(u"Manage or add subscriptions.")

    editform_factory = ManageSubscriptionsFormEdit

    @property
    def batch_size(self):
        if self._fulltext_query():
            # We don't support batching when we search
            return 0
        else:
            return 30

    @property
    def prefix(self):
        return self.format

    def _composer_fields(self):
        return field.Fields(self.composer.schema)

    def _collector_fields(self):
        if self.context.collector is not None:
            return field.Fields(self.context.collector.schema)
        return field.Fields()

    def _fulltext_query(self):
        return self.request.form.get('search.widgets.fulltext')

    @property
    def update_schema(self):
        fields = self._composer_fields()
        fields += self._collector_fields()
        return fields

    def get_items(self):
        items = []

        query = dict(format=self.format)
        search = self._fulltext_query()
        if search:
            query['fulltext'] = search

        for subscription in self.context.subscriptions.query(**query):
            if subscription.metadata['format'] == self.format:
                items.append((str(subscription.secret), subscription))
        return items

    def add(self, data):
        secret = collective.singing.subscribe.secret(
            self.context, self.composer, data, self.request)

        composer_data = dict(
            [(name, value) for (name, value) in data.items()
             if name in self._composer_fields()])

        collector_data = dict(
            [(name, value) for (name, value) in data.items()
             if name in self._collector_fields()])

        metadata = dict(format=self.format,
                        date=datetime.datetime.now())

        try:
            return aq_inner(self.context).subscriptions.add_subscription(
                self.context, secret, composer_data, collector_data, metadata)
        except ValueError, e:
            raise schema.ValidationError(e.args[0])

    def remove(self, (secret, item)):
        subs = aq_inner(self.context).subscriptions.query(secret=secret,
                                                format=item.metadata['format'])
        for subscription in subs:
            aq_inner(self.context).subscriptions.remove_subscription(subscription)


class SubscriptionChoiceFieldDataManager(z3c.form.datamanager.AttributeField):
    # This nasty hack allows us to have the default IDataManager to
    # use a different schema for adapting the context.  This is
    # necessary because the schema that
    # ``collector.SmartFolderCollector.schema`` produces is a
    # dynamically generated interface.
    #
    # ``collector.SmartFolderCollector.schema`` should rather produce
    # an interface with fields that already have the right interface
    # to adapt to as their ``interface`` attribute.
    component.adapts(
        collective.singing.subscribe.SimpleSubscription,
        zope.schema.interfaces.IField)

    def __init__(self, context, field):
        super(SubscriptionChoiceFieldDataManager, self).__init__(context, field)
        if self.field.interface is not None:
            if issubclass(self.field.interface, ICollectorSchema):
                self.field.interface = ICollectorSchema

class ChannelPreviewForm(z3c.form.form.Form):
    """Channel preview form.

    Currently only allows an in-browser preview.
    """

    interface.implements(ISendAndPreviewForm)

    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')
    description = _(u"See an in-browser preview of the newsletter.")

    fields = z3c.form.field.Fields(ISendAndPreviewForm).select(
        'include_collector_items')

    include_collector_items = True

    def getContent(self):
        return self

    @z3c.form.button.buttonAndHandler(_(u"Generate"), name='preview')
    def handle_preview(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = form.EditForm.formErrorsMessage
            return

        collector_items = int(bool(data['include_collector_items']))

        return self.request.response.redirect(
            self.context.absolute_url()+\
            '/preview-newsletter.html?include_collector_items=%d' % \
            collector_items)

class EditChannelForm(z3c.form.form.EditForm):
    """Channel edit form.

    As opposed to the crud form, this allows editing of all channel
    settings.

    Actions are also provided to preview and send the newsletter.
    """

    template = viewpagetemplatefile.ViewPageTemplateFile('form.pt')

    description = _(u"Edit the properties of the mailing-list.")

    @property
    def fields(self):
        fields = z3c.form.field.Fields(IChannel).select('title')

        collector = schema.Choice(
            __name__='collector',
            title=IChannel['collector'].title,
            required=False,
            vocabulary='Collector Vocabulary')

        scheduler = FactoryChoice(
            __name__='scheduler',
            title=IChannel['scheduler'].title,
            required=False,
            vocabulary='Scheduler Vocabulary')

        fields += field.Fields(collector, scheduler)
        fields += field.Fields(IChannel).select(
            'description', 'subscribeable', 'keep_sent_messages')
        fields['description'].widgetFactory[
            z3c.form.interfaces.INPUT_MODE] = wysiwyg.WysiwygFieldWidget

        return fields


def parseSubscriberCSVFile(subscriberdata, composer,
                           header_row_present=False,
                           delimiter=csv_delimiter):
    """parses file containing subscriber data

    returns list of dictionaries with subscriber data according to composer"""
    properties = component.getUtility(IPropertiesTool)
    charset = properties.site_properties.getProperty('default_charset',
                                                     'utf-8').upper()
    try:
        data = cStringIO.StringIO(subscriberdata)
        reader = csv.reader(data, delimiter=str(delimiter))
        subscriberslist = []
        errorcandidates = []
        for index, parsedline in enumerate(reader):
            if index == 0:
                if header_row_present:
                    fields = parsedline
                    continue
                else:
                    fields = field.Fields(composer.schema).keys()
            if len(parsedline)<len(fields):
                pass
            else:
                try:
                    subscriber = dict(zip(fields,\
                       map(lambda x:x.decode(charset), parsedline)))
                    subscriber['email'] = subscriber['email'].lower()
                    check_email(subscriber['email'])
                except:
                    errorcandidates.append(subscriber['email'])
                else:
                    subscriberslist.append(subscriber)
        return subscriberslist, errorcandidates
    except Exception, e:
        return _(u"Error importing subscriber file. %s" % e), []

class ExportCSV(BrowserView):

    def __call__(self):
        properties = component.getUtility(IPropertiesTool)
        charset = properties.site_properties.getProperty('default_charset',
                                                         'utf-8').upper()
        self.request.response.setHeader('Content-Type',
                                        'text/csv; charset=%s' % charset)
        self.request.response.setHeader('Content-disposition',
            'attachment; filename=subscribers_%s_%s.csv' % (self.context.id,
                                      datetime.date.today().strftime("%Y%m%d")))
        res = cStringIO.StringIO()
        writer = csv.writer(res, dialect=csv.excel, delimiter=csv_delimiter)
        for format in self.context.composers.keys():
            for subscription in tuple(self.context.subscriptions.query(format=format)):
                row = []
                for item in field.Fields(self.context.composers[format].schema).keys():
                    v = subscription.composer_data.get(item) or ''
                    row.append(self._convertValue(v, charset))

                writer.writerow(row)
        return res.getvalue()

    def _convertValue(self, value, charset='utf-8'):
        # here we properly handle lists, booleans and strings
        if isinstance(value, (types.TupleType, types.ListType)):
            value = ', '.join(map(lambda x:x.encode(charset), value))
        elif isinstance(value, bool):
            value = str(value)
        elif isinstance(value, datetime.datetime):
            value = value.strftime('%d/%m/%Y %H:%M:%S')
        else:
            value = value.encode(charset)
        return value


class UploadForm(crud.AddForm):
    label = _(u"Upload")

    @property
    def fields(self):
        subscriberdata = schema.Bytes(
            __name__ = 'subscriberdata',
            title=_(u"Subscribers"),
            description=_(u"Upload a CSV file with a list of subscribers here. "
                          u"Subscribers already present in the database will "
                          u"be overwritten. Each line should contain: "
                          u"${columns}.",
                          mapping=dict(columns=';'.join(field.Fields(
                                         self.context.composer.schema).keys())))
        )
        onlyremove = schema.Bool(__name__ = 'onlyremove',
            title=_(u"Remove subscribers in list."),
            description=_(u"Only purge subscribers present in this list."),
            default = False
        )
        remove = schema.Bool(__name__ = 'removenonexisting',
            title=_(u"Purge list."),
            description=_(u"Purge list before import."),
            default = False
        )
        header_row_present = schema.Bool(__name__ = 'header_row_present',
            title=_(u"CSV contains a header row"),
            description=_(u"Select this if you want to use the csv "
                          u"header row to designate document variables."
                          u"The header row must contain one 'email' field."),
            default = False
        )
        csv_delimiter = schema.TextLine(__name__ = 'csv_delimiter',
            title=_(u"CSV delimiter"),
            description=_(u"The delimiter in your CSV file. "
                          u"(Usually ',' or ';', but no quotes are necessary.)"),
            default = u','
        )

        return field.Fields(subscriberdata, remove, onlyremove,
                            header_row_present, csv_delimiter)

    @property
    def mychannel(self):
        return self.context.context

    def _releaseSubscribers(self):
        # UNUSED CODE?
        subs = self.mychannel.subscriptions.query(format=self.context.format)
        for subscription in subs:
            self.mychannel.subscriptions.remove_subscription(subscription)

    def _removeSubscription(self, secret):
        """Removes subscription based on secret.
        """
        current = self.mychannel.subscriptions
        old_subscription = current.query(format=self.context.format,
                                        secret=secret)
        if not len(old_subscription):
            return None
        old_subscription = tuple(old_subscription)
        old_collector_data = old_subscription[0].collector_data
        for sub in old_subscription:
            current.remove_subscription(sub)
        return old_subscription

    def _addItem(self, data):
        """imports csv and returns message

        @param data: the form data
        @return status as i18n aware unicode

        if a subscription with same email is found, we delete this first
        but keep selection of options.

        if remove-non-existing in the form was found, all existing subscriptions
        not found in the CSV file are removed.
        """

        metadata = dict(format=self.context.format,
                        date=datetime.datetime.now())

        subscriberdata = data.get('subscriberdata', None)
        onlyremove = data.get('onlyremove', False)
        remove = data.get('removenonexisting', False)
        header_row_present = data.get('header_row_present', False)
        delimiter = data.get('csv_delimiter', csv_delimiter)
        if subscriberdata is None:
            return _(u"File was not given.")
        subscribers, errorcandidates = parseSubscriberCSVFile(subscriberdata,
                                self.context.composer,
                                header_row_present=header_row_present,
                                delimiter=delimiter)
        if not type(subscribers)==type([]):
            return _(u"File has incorrect format.")
        added = 0
        new_and_updated = []
        notadded = len(errorcandidates)
        current = self.mychannel.subscriptions
        if onlyremove:
            new_and_updated = [s['email'] for s in subscribers]
        if onlyremove or remove:
            old = sets.Set([sub.composer_data['email'] \
                            for sub in current.values()])
        # maybe add subscribvers or just registered subscribers email list
        if not onlyremove:
            for subscriber_data in subscribers:
                secret = collective.singing.subscribe.secret(self.mychannel,
                                                             self.context.composer,
                                                             subscriber_data,
                                                             self.context.request)
                try:
                    old_subscription = self._removeSubscription(secret)
                    item = current.add_subscription(self.mychannel, secret,
                                                    subscriber_data, [], metadata)
                    new_and_updated.append(subscriber_data['email'])
                    # restore section selection
                    if old_subscription is not None:
                        old_collector_data = old_subscription[0].collector_data
                        if 'selected_collectors' in old_collector_data \
                           and old_collector_data['selected_collectors']:
                            item.collector_data = old_collector_data
                    added += 1
                except Exception, e: # XXX refine which exceptions we want to catch
                    # TODO; put some information about error e into the message
                    errorcandidates.append(subscriber_data.get('email',
                                                               _(u'Unknown')))
                    notadded += 1
        removed = 0
        if onlyremove or remove:
            to_remove = old.difference(sets.Set(new_and_updated))
            if onlyremove:
                to_remove = new_and_updated
            for email in to_remove:
                for key in current.keys():
                    if key.startswith(email):
                        current.remove_subscription(current[key])
                        removed += 1
                        break
        if onlyremove:
            msg = _(u"${numberremoved} subscriptions removed successfully!",
                    mapping=dict(numberremoved=str(removed),))
        elif notadded:
            msg = _(u"${numberadded} subscriptions updated successfully. "
                    u"${numberremoved} removed. "
                    u"${numbernotadded} could not be added. "
                    u"(${errorcandidates})",
                    mapping=dict(numbernotadded=str(notadded),
                                 numberremoved=str(removed),
                                 errorcandidates=', '.join(errorcandidates),
                                 numberadded=str(added))
                    )
        elif removed > 0:
            msg = _(u"${numberadded} subscriptions updated successfully, "
                    u"${numberremoved} removed!",
                    mapping=dict(numberadded=str(added),
                                 numberremoved=str(removed))
                    )
        else:
            msg = _(u"${numberadded} subscriptions updated successfully!",
                    mapping=dict(numberadded=str(added),))
        return msg

    @z3c.form.button.buttonAndHandler(_('Upload'), name='upload')
    def handle_add(self, action):
        data, errors = self.extractData()
        onlyremove = data.get('onlyremove', False)
        remove = data.get('removenonexisting', False)
        cannot_remove_onlyremove = (remove and onlyremove)
        if errors or cannot_remove_onlyremove:
            self.status = form.EditForm.formErrorsMessage
            if cannot_remove_onlyremove:
                self.status = _(
                    u'You can not add things in purge only mode!'
                )
            return
        try:
            self.status = self._addItem(data)
        except Exception, e:
            if DevelopmentMode:
                raise
            self.status = e

    @z3c.form.button.buttonAndHandler(_('Download'), name='download')
    def handle_download(self, action):
        self.status = _(u"Subscribers exported.")
        return self.request.response.redirect(self.mychannel.absolute_url() + \
                                              '/export')

class ManageUploadForm(crud.CrudForm):
    description = _(u"Upload list of subscribers.")

    format = None
    composer = None

    editform_factory = crud.NullForm
    addform_factory = UploadForm

    @property
    def prefix(self):
        return self.format


class EditComposersForm(z3c.form.form.EditForm):
    """
    """
    template = viewpagetemplatefile.ViewPageTemplateFile(
        'form-with-subforms.pt')
    subforms = []
    ignoreContext = True
    semiSuccesMessage = _(u"Only some of your changes were saved")

    def update(self):
        super(EditComposersForm, self).update()
        self.update_subforms()

    def update_subforms(self):
        self.subforms = []
        for format, item in self.context.composers.items():
            subform = component.getMultiAdapter(
               (item, self.request, self),
               z3c.form.interfaces.ISubForm)
            subform.format = format
            subform.update()
            self.subforms.append(subform)

    @z3c.form.button.buttonAndHandler(_('Save'), name='save')
    def handleSave(self, action):
        self.status = ''
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return
        changes = self.applyChanges(data)
        if not changes:
            self.update_subforms()
            stati = [f.status for f in self.subforms]
            if self.successMessage in stati:
                if self.formErrorsMessage not in stati:
                    self.status = self.successMessage
                else:
                    self.status = self.semiSuccesMessage
            elif self.formErrorsMessage in stati:
                self.status = self.formErrorsMessage
        if not self.status:
            if changes:
                self.status = self.successMessage
            else:
                self.status = self.noChangesMessage


class ManageChannelView(BrowserView):
    """Manage channel view.

    Shows subscription, preview and edit options.
    """

    __call__ = ViewPageTemplateFile('controlpanel.pt')
    preview_form = ChannelPreviewForm
    edit_form = EditChannelForm
    composers_form = EditComposersForm

    @property
    def back_link(self):
        return dict(label=_(u"Up to Mailing-lists administration"),
                    url=self.context.aq_inner.aq_parent.absolute_url())

    @property
    def label(self):
        return _(u'Edit Mailing-list ${channel}',
                 mapping={'channel':self.context.title})

    def contents(self):
        switch_on(self,
                  request_layer=collective.singing.interfaces.IFormLayer)

        fieldsets = []

        # Add the subscriptions tab:
        forms = []
        for format, composer in self.context.composers.items():
            form = ManageSubscriptionsForm(self.context, self.request)
            form.format = format
            form.composer = composer
            forms.append(form)

            form = ManageUploadForm(self.context, self.request)
            form.format = format
            form.composer = composer
            forms.append(form)
        fieldsets.append((_(u"Subscriptions"), '\n'.join([form() for form in forms])))

        # Add edit, composers and preview tabs:
        fieldsets.append((_(u"Edit"), self.edit_form(self.context, self.request)()))
        fieldsets.append((_(u"Composers"), self.composers_form(self.context, self.request)()))
        fieldsets.append((_(u"Preview"), self.preview_form(self.context, self.request)()))

        wrapper = """<dl class="enableFormTabbing">%s</dl>"""
        template = """
        <dt id="fieldsetlegend-%d">%s</dt>
        <dd id="fieldset-%d">
          %s
        </dd>
        """

        return wrapper % \
               ("\n".join((template % (id(msg), zope.i18n.translate(msg, context=self.request), id(msg), html)
                           for (msg, html) in fieldsets)))
