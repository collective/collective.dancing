import re
import urlparse
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

    @property
    def context_url(self):
        url = self.context.absolute_url()
        if url.endswith('/'):
            return url[:-1]
        return url

    @property
    def site_url(self):
        site = component.getUtility(IPloneSiteRoot)
        url = utils.fix_request(site, 0).absolute_url()
        if url.endswith('/'):
            return url[:-1]
        return url

    def _base(self):
        if self.base is None:
            return self.site_url

        url = self.base
        if url.endswith('/'):
            return url[:-1]
        return url

    def __call__(self, text, subscription):
        anchor_exp = re.compile('#\w+')
        root_exp = re.compile('^/')
        relative_exp = re.compile('^(?!(\w+://|mailto:|javascript:|/))')
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

                # Kupu makes absolute links without the domain, which
                # include the Plone site, so let's try and strip the
                # Plone site's id out:
                site_id = component.getUtility(IPloneSiteRoot).getId()
                if tag[attr].startswith('/%s/' % site_id):
                    tag[attr] = tag[attr].replace('/%s/' % site_id, '/', 1)

                tag[attr] = '%s%s' % (self.site_url, tag[attr])

            for tag in soup.findAll(SoupStrainer(**{attr:relative_exp})):
                if tag[attr].startswith('#'):
                    tag[attr] = self.context_url + tag[attr]
                    continue

                parts = (self.context_url + '/'+ tag[attr]).split('/')
                while '..' in parts:
                    dots = parts.index('..')
                    del parts[dots-1:dots+1]
                tag[attr] = '/'.join(parts)

            for tag in soup.findAll(SoupStrainer(**{attr:anchor_exp})):
                prot, dom, path, params, query, frag =  urlparse.urlparse(tag[attr])

                if not prot or not dom:
                    tag[attr] = '#%s' % frag
                    continue

                url = '%s://%s%s' % (prot, dom, path)
                if url.endswith('/'):
                    url = url[:-1]

                # If the url points to our context and the anchor exists in our
                # text we change it to a bare anchor.
                # XXX: Maybe this should work with links to non-default views.
                if url == self.context_url:
                    for match in soup.findAll(attrs=dict(name=frag)):
                        if match.name == u'a':
                            tag[attr] = '#%s' % frag

            # Check for aliases
            if self.aliases:
                for tag in soup.findAll(SoupStrainer(**{attr:alias_exp})):
                    p = re.compile('^(\w+://)(%s)(/?)(.*)' %
                                   '|'.join(self.aliases),
                                   re.IGNORECASE)
                    tag[attr] = p.sub(r'%s\3\4' % self._base(), tag[attr])

        return str(soup)
