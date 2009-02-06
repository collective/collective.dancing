import os
from setuptools import setup, find_packages
from xml.dom.minidom import parse

def readversion():
    mdfile = os.path.join(os.path.dirname(__file__), 'collective', 'dancing', 
                          'profiles', 'default', 'metadata.xml')
    metadata = parse(mdfile)
    assert metadata.documentElement.tagName == "metadata"
    return metadata.getElementsByTagName("version")[0].childNodes[0].data

def read(*pathnames):
    return open(os.path.join(os.path.dirname(__file__), *pathnames)).read()

setup(name='collective.dancing',
      version=readversion().strip(),
      description="The all-singing all-dancing newsletter product for Plone.",
      long_description='\n'.join([
          read('docs', 'README.txt'),
          read('docs', 'THANKS.txt'),
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
          'collective.singing>0.6.10',
          'plone.z3cform>=0.5.1',
          'plone.app.z3cform>=0.4.2',
          'five.intid',
          'zc.lockfile',
          'StoneageHTML',
          'BeautifulSoup',
      ],
      
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
