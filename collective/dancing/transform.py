import re
from BeautifulSoup import BeautifulSoup, SoupStrainer

from zope import interface
from zope import component

from Products.CMFPlone.interfaces import IPloneSiteRoot
import collective.singing.interfaces

from collective.dancing import utils

class URL(object):
    interface.implements(collective.singing.interfaces.ITransform)

    base = None
    aliases = []
    
    def __init__(self, context):
        self.context = context
 
    def _base(self):
        if self.base is None:
            site = component.getUtility(IPloneSiteRoot)
            url = utils.fix_request(site, 0).absolute_url()
        else:
            url = self.base

        if url.endswith('/'):
            return url[:-1]
        else:
            return url

    def __call__(self, text, subscription):
        root_exp = re.compile('^/')
        relative_exp = re.compile('^(?!(\w+://|/))')
        alias_exp = re.compile('|'.join(self.aliases), re.IGNORECASE)
        soup = BeautifulSoup(text, fromEncoding='UTF-8') # hmm
        curl = self.context.absolute_url()
        curl_parts = curl.split('/')

        for attr in ('href', 'src'):
            for tag in soup.findAll(SoupStrainer(**{attr:root_exp})):
                if len(curl_parts) > 3 and \
                       ':' in curl_parts[2] and \
                       tag[attr].startswith('/%s/' % curl_parts[3]):
                    tag[attr] = '/'+'/'.join(tag[attr].split('/')[2:])

                    # Kupu makes absolute links without the domain,
                    # which include the Plone site, so let's try and
                    # strip the Plone site's id out:
                site_id = component.getUtility(IPloneSiteRoot).getId()
                if tag[attr].startswith('/%s/' % site_id):
                    tag[attr] = tag[attr].replace('/%s/' % site_id, '/', 1)

                tag[attr] = '%s%s' % (self._base(), tag[attr])

            for tag in soup.findAll(SoupStrainer(**{attr:relative_exp})):
                first = curl.endswith('/') and curl or curl + '/'
                parts = (first + tag[attr]).split('/')
                while '..' in parts:
                    dots = parts.index('..')
                    del parts[dots-1:dots+1]
                tag[attr] = '/'.join(parts)

            # Check for aliases
            if self.aliases:
                for tag in soup.findAll(SoupStrainer(**{attr:alias_exp})):
                    p = re.compile('^(\w+://)(%s)(/?)(.*)' %
                                   '|'.join(self.aliases),
                                   re.IGNORECASE)
                    tag[attr] = p.sub(r'%s\3\4' % self._base(), tag[attr])
            
        return str(soup)
