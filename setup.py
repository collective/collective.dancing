from setuptools import setup, find_packages

def read(name):
    return open(name).read()

version = '0.9.10'

setup(name='collective.dancing',
      version=version,
      description="The all-singing all-dancing newsletter add-on for Plone.",
      long_description='\n'.join([
          read('README.txt'),
          read('THANKS.txt'),
          read('CHANGES.txt'),
          ]),
      classifiers=[
        "Framework :: Plone",
        'Framework :: Plone :: 4.0',
        'Framework :: Plone :: 4.1',
        "Framework :: Zope2",
        "Programming Language :: Python",
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
          'collective.singing>=0.7.1',
          'plone.z3cform>=0.5.1',
          'plone.app.z3cform>=0.5',
          'five.intid',
          'zc.lockfile',
          'StoneageHTML',
          'BeautifulSoup',
          'collective.monkeypatcher',
          'zope.testbrowser',
      ],
      entry_points="""
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
