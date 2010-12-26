# We patch our friend, the ATTopic to allow overriding *all* of the
# query that it builds by providing keyword arguments.

from Products.ATContentTypes.content.topic import *

def queryCatalog(self, REQUEST=None, batch=False, b_size=None,
                                                full_objects=False, **kw):
    """Invoke the catalog using our criteria to augment any passed
        in query before calling the catalog.
    """
    if REQUEST is None:
        REQUEST = getattr(self, 'REQUEST', {})
    b_start = REQUEST.get('b_start', 0)

    pcatalog = getToolByName(self, 'portal_catalog')
    mt = getToolByName(self, 'portal_membership')
    related = [ i for i in self.getRelatedItems() \
                    if mt.checkPermission(View, i) ]
    if not full_objects:
        uids = [r.UID() for r in related]
        query = dict(UID=uids)
        related = pcatalog(query)
    related=LazyCat([related])

    limit = self.getLimitNumber()
    max_items = self.getItemCount()
    # Batch based on limit size if b_size is unspecified
    if max_items and b_size is None:
        b_size = int(max_items)
    else:
        b_size = b_size or 20

    q = self.buildQuery()
    if q is None:
        results=LazyCat([[]])
    else:
        # Allow parameters to further limit existing criterias
        q.update(kw)
        if not batch and limit and max_items and self.hasSortCriterion():
            q.setdefault('sort_limit', max_items)
        if batch:
            q['b_start'] = b_start
            q['b_size'] = b_size
        __traceback_info__ = (self, q)
        results = pcatalog.searchResults(REQUEST, **q)

    if limit and not batch:
        if full_objects:
            return related[:max_items] + \
                   [b.getObject() for b in results[:max_items-len(related)]]
        return related[:max_items] + results[:max_items-len(related)]
    elif full_objects:
        results = related + LazyCat([[b.getObject() for b in results]])
    else:
        results = related + results
    if batch:
        batch = Batch(results, b_size, int(b_start), orphan=0)
        return batch
    return results

