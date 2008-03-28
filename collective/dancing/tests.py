import unittest
from zope.testing import doctest
from Testing import ZopeTestCase as ztc
from Products.Five import zcml
from Products.Five import fiveconfigure
from Products.PloneTestCase import PloneTestCase as ptc
from Products.PloneTestCase.layer import onsetup

import collective.dancing

def setup_error_log(site):
    site.error_log._ignored_exceptions = ()
    def print_error(index=0):
        logs = site.error_log.getLogEntries()
        if logs:
            print logs[index]['tb_text']
    return print_error

@onsetup
def setUp():
    fiveconfigure.debug_mode = True
    zcml.load_config('configure.zcml', collective.dancing)
    fiveconfigure.debug_mode = False
    ztc.installPackage('collective.dancing')

setUp()
ptc.setupPloneSite(products=['collective.dancing'])

def test_suite():
    return unittest.TestSuite([

        doctest.DocTestSuite('collective.dancing.channel'),
        doctest.DocTestSuite('collective.dancing.composer'),

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
            test_class=ptc.PloneTestCase,
            ),

        ztc.ZopeDocFileSuite(
            'browser.txt',
            test_class=ptc.FunctionalTestCase,
            ),
        ])
