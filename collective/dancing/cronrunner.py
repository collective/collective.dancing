

from collective.cron import crontab
class SingingCronJob(crontab.Runner):
    def run(self):
        print "foo"