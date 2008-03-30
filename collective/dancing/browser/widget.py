import zope.interface
import zope.schema.interfaces
import zope.app.component.hooks
import Acquisition

import z3c.form.interfaces
import z3c.form.browser.textarea
import z3c.form.widget

class IWysiwygWidget(z3c.form.interfaces.ITextAreaWidget):
    pass

class WysiwygWidget(z3c.form.browser.textarea.TextAreaWidget):
    """
      >>> from z3c.form.testing import TestRequest
      >>> from collective.dancing.browser.widget import WysiwygWidget
      >>> widget = WysiwygWidget(TestRequest())
      >>> widget.context = portal.events
      >>> widget.name = 'bar'
      >>> widget.update()
      >>> output = widget.render()
      >>> 'kupu' in output
      True
    """
    zope.interface.implementsOnly(IWysiwygWidget)
    
    klass = u'kupu-widget'
    value = u''

    def update(self):
        super(z3c.form.browser.textarea.TextAreaWidget, self).update()
        z3c.form.browser.widget.addFieldClass(self)

@zope.component.adapter(zope.schema.interfaces.IField,
                        z3c.form.interfaces.IFormLayer)
@zope.interface.implementer(z3c.form.interfaces.IFieldWidget)
def WysiwygFieldWidget(field, request):
    """IFieldWidget factory for WysiwygWidget."""
    return z3c.form.widget.FieldWidget(field, WysiwygWidget(request))
