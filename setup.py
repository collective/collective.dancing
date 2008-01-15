from setuptools import setup, find_packages

version = '0.1'

setup(name='collective.dancing',
      version=version,
      description="",
      long_description="""\
""",

      classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Topic :: Software Development :: Libraries :: Python Modules",
        ],
      keywords='',
      author='Plone Foundation',
      author_email='',
      url='',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective'],
      include_package_data=True,
      zip_safe=False,

      # If the dependency to z3c.form gives you trouble within a Zope
      # 2 environment, try the `fakezope2eggs` recipe
      install_requires=[
          'setuptools',
          'collective.singing',
      ],
      
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
