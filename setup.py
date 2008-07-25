import os
from setuptools import setup, find_packages

version = '0.5.0'

def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()

setup(name='collective.dancing',
      version=version,
      description="The all-singing all-dancing newsletter product for Plone.",
      long_description='\n'.join([
          read('docs', 'README.txt'),
          read('docs', 'HISTORY.txt'),
          ]),
      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='zope plone notification newsletter',
      author='Daniel Nouri, Thomas Clement Mogensen and contributors',
      author_email='singing-dancing@googlegroups.com',
      url='http://plone.org/products/dancing',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,

      # If the dependency to z3c.form gives you trouble within a Zope
      # 2 environment, try the `fakezope2eggs` recipe
      install_requires=[
          'setuptools',
          'collective.singing>=0.5dev',
          'plone.z3cform>=0.4dev',
          'plone.app.z3cform>=0.3dev',
          'five.intid',
          'StoneageHTML',
      ],
      
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
