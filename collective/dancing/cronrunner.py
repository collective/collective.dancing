

from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManager import setSecurityPolicy 
from Testing.makerequest import makerequest 
from Products.CMFCore.tests.base.security import PermissiveSecurityPolicy, OmnipotentUser


from collective.cron import crontab
class SingingCronJob(crontab.Runner):
    def run(self):

        portal = self.context

        # not quite sure where to get a requet from
        newSecurityManager(None, OmnipotentUser().__of__(portal.acl_users))
        portal = makerequest(portal)
        utilsview = portal.unrestrictedTraverse("@@dancing.utils")

        import pdb; pdb.set_trace()
        utilsview._tick_and_dispatch()
