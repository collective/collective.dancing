import os.path
from z3c.form import form
from collective.dancing import browser

SubFormTemplateFactory = form.FormTemplateFactory(
    os.path.join(os.path.dirname(browser.__file__), 'subform.pt'))
