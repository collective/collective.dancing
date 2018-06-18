# -*- coding: utf-8 -*-
from setuptools import find_packages
from setuptools import setup

import os


def read(*paths):
    return open(os.path.join(os.path.dirname(__file__), *paths)).read()


version = '1.2'

setup(name='collective.dancing',
      version=version,
      description="The all-singing all-dancing newsletter add-on for Plone.",
      long_description='\n'.join([
          read('README.rst'),
          read('docs', 'THANKS.rst'),
          read('docs', 'CHANGES.rst'),
      ]),
      classifiers=[
          "Framework :: Plone",
          "Framework :: Plone :: 4.3",
          "Framework :: Plone :: 4.2",
          "Framework :: Zope2",
          "Programming Language :: Python",
      ],
      keywords='zope plone notification newsletter',
      author='Daniel Nouri, Thomas Clement Mogensen and contributors',
      author_email='singing-dancing@googlegroups.com',
      url='http://plone.org/products/dancing',
      download_url="""
      https://github.com/collective/collective.dancing/tarball/1.0.2
      """,
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,

      # If the dependency to z3c.form gives you trouble within a Zope
      # 2 environment, try the `fakezope2eggs` recipe
      install_requires=[
          'setuptools',
          'collective.singing>=0.7.1',
          'plone.z3cform>=0.5.1',
          'plone.app.z3cform>=0.5',
          'five.intid',
          'zc.lockfile',
          'StoneageHTML',
          'BeautifulSoup',
          'collective.monkeypatcher',
      ],
      extras_require={
          'test': [
              'zope.testbrowser',
              'Products.PloneTestCase',
          ],
      },
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
