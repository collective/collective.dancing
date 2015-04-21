from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SecurityManagement import setSecurityManager
from Testing.makerequest import makerequest
from collective.cron import crontab


class SingingCronJob(crontab.Runner):
    def run(self):

        cron = self.cron
        portal = self.context
        user = portal.acl_users.getUser(cron.user)
        newSecurityManager(None, user)
        portal = makerequest(portal)

        dancing_utils = portal.unrestrictedTraverse("@@dancing.utils")
        dancing_utils._tick_and_dispatch()

        setSecurityManager(None)
