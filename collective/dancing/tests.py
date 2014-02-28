import re
import unittest
from zope import interface, component, schema
import zope.sendmail.interfaces
from zope.testing import doctest
from zope.component import testing
from Testing import ZopeTestCase as ztc
from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

from email.Parser import Parser
from email.Header import Header, decode_header
from email.Charset import Charset, QP, SHORTEST
from copy import deepcopy

from collective.singing.interfaces import ISubscription
import collective.dancing
import collective.dancing.utils
from collective.dancing.composer import HTMLComposer
from collective.dancing.interfaces import IHTMLComposer
from collective.dancing.composer import PrimaryLabelTextLine


# custom composer definition
class IMyComposerSchema(interface.Interface):
    name = schema.TextLine(title=u"Name")
    email = PrimaryLabelTextLine(title=u"E-mail address")
    programmer = schema.Bool(title=u"Are you a programmer?")
    interests = schema.Tuple(
        title=u"Interests",
        value_type=schema.Choice(values=('Plone', 'Zope', 'Python')))
    registered = schema.Datetime(title=u"Date of registration")

class MyComposer(HTMLComposer):
  title = u'My Composer'
  schema = IMyComposerSchema

@component.adapter(ISubscription)
@interface.implementer(IMyComposerSchema)
def composerdata_from_subscription(subscription):
    return collective.dancing.utils.AttributeToDictProxy(
        subscription.composer_data)


def setup_error_log(site):
    site.error_log._ignored_exceptions = ()
    def print_error(index=0):
        logs = site.error_log.getLogEntries()
        if logs:
            print logs[index]['tb_text']
    return print_error

def replace_with_fieldindex(name, site):
    site.portal_catalog.delIndex(name)
    site.portal_catalog.addIndex(name, 'FieldIndex')
    site.portal_catalog.manage_reindexIndex((name,))

@onsetup
def setUp():
    fiveconfigure.debug_mode = True
    zcml.load_config('configure.zcml', collective.dancing)
    fiveconfigure.debug_mode = False
    ztc.installPackage('collective.dancing')

setUp()
ptc.setupPloneSite(products=['collective.dancing'])

def decodeMessageAsString(msg):
    """ This helper method takes Message object or string and returns
        string which does not contain base64 encoded parts
        Returns message without any encoding in parts
    """
    if isinstance(msg, str):
        msg = Parser().parsestr(msg)

    new = deepcopy(msg)
    # From is utf8 encoded: '=?utf-8?q?Site_Administrator_=3C=3E?='
    new.replace_header('From', decode_header(new['From'])[0][0])
    new.replace_header('Subject', decode_header(new['Subject'])[0][0])
    charset = Charset('utf-8')
    charset.header_encoding = SHORTEST
    charset.body_encoding   = QP
    charset.output_charset  = 'utf-8'

    for part in new.walk():
        if part.get_content_maintype()=="multipart":
            continue
        decoded = part.get_payload(decode=1)
        del part['Content-Transfer-Encoding']
        part.set_payload(decoded, charset)

    return new.as_string()

def setup_testing_maildelivery():
    class TestingMailDelivery(object):

        interface.implements(zope.sendmail.interfaces.IMailDelivery)
        sent = []

        def send(self, from_, to, message):
            print '*TestingMailDelivery sending*:'
            print 'From:', decode_header(from_)[0][0]
            print 'To:', ', '.join(to)
            print 'Message follows:'
            decoded = decodeMessageAsString(message)
            print decoded
            self.sent.append(decoded)

        @classmethod
        def last_messages(klass, purge=True):
            klass.order()
            value = '\n'.join(klass.sent)
            if purge:
                klass.sent = []
            return value

        @classmethod
        def order(klass):
            klass.sent = sorted(
                klass.sent,
                key=lambda msg: re.findall('To: .*$', msg, re.MULTILINE))

    delivery = TestingMailDelivery()
    component.provideUtility(delivery)
    return TestingMailDelivery

from Products.Five import testbrowser
from zope.testbrowser import browser
import mechanize

class PublisherMechanizeBrowser(mechanize.Browser):
    """Special ``mechanize`` browser using the Zope Publisher HTTP handler."""

    default_schemes = ['http']
    default_others = ["_unknown", "_http_error", "_http_default_error"]
    default_features = ['_redirect', '_cookies', '_referer', '_refresh',
                        '_equiv', '_basicauth', '_digestauth',]

    def __init__(self, *args, **kws):
        inherited_handlers = ['_unknown', '_http_error',
            '_http_default_error', '_basicauth',
            '_digestauth', '_redirect', '_cookies', '_referer',
            '_refresh', '_equiv', '_gzip']
        self.handler_classes = {"http": testbrowser.PublisherHTTPHandler}
        for name in inherited_handlers:
            self.handler_classes[name] = mechanize.Browser.handler_classes[name]
        mechanize.Browser.__init__(self, *args, **kws)

class Browser(browser.Browser):
    """overrides zope.testbrowser Browser to support nested forms (use of a recent mechanize version)"""
    def __init__(self, url=None):
        mech_browser = PublisherMechanizeBrowser()
        mech_browser.handler_classes["http"] = testbrowser.PublisherHTTPHandler
        super(Browser, self).__init__(url=url, mech_browser=mech_browser)

class DancingTestCase(ptc.FunctionalTestCase):
    """set expected email_from_name to help tests pass in Plone 4"""
    def afterSetUp(self):
        #in plone4 email_from_name is not set.
        prop = {'email_from_name':u'Site Administrator'}
        self.portal.portal_properties.site_properties.editProperties(prop)

def test_suite():
    return unittest.TestSuite([
        doctest.DocTestSuite('collective.dancing.channel'),
        doctest.DocTestSuite('collective.dancing.composer'),
        doctest.DocTestSuite('collective.dancing.utils'),

        doctest.DocFileSuite('transform.txt'),

        ztc.ZopeDocFileSuite(
            'channel.txt',
            test_class=ptc.PloneTestCase,
        ),

        ztc.ZopeDocFileSuite(
            'collector.txt',
            test_class=ptc.PloneTestCase,
        ),

        ztc.ZopeDocFileSuite(
            'composer.txt',
            test_class=DancingTestCase,
        ),

        ztc.ZopeDocFileSuite(
            'browser.txt',
            test_class=DancingTestCase,
            encoding='utf-8'
        ),
        ztc.ZopeDocFileSuite(
            'portlets.txt',
            test_class=DancingTestCase,
        ),
        doctest.DocTestSuite(
            'collective.dancing.composer',
            setUp=testing.setUp, tearDown=testing.tearDown,
        ),
    ])
