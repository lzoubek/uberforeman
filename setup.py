import sys
import os

VERSION = '1.2.1'
py_vers_tag = '-%s.%s' % sys.version_info[:2]

try:
    from setuptools import setup
    from setuptools import find_packages
    addl_args = dict(
        zip_safe = False,
        packages = find_packages(),
        entry_points = {
        'console_scripts': [
            'uberforeman = uberforeman:main',
            'uberforeman%s = uberforeman:main' % py_vers_tag,
            ],
        },
        )

except ImportError:
    from distutils.core import setup
    addl_args = dict(
        packages = ['uberforeman'],
        scripts = ['bin/uberforeman'],
        )
setup(
    name = 'uberforeman',
    version = VERSION,
    author = 'Libor Zoubek',
    author_email = 'lzoubek@redhat.com',
    description = ('uberforeman is a CLI tool to foreman that can manage and deploy multi-host setups'),
    long_description = \
    """
    tbd...
    """,

    license = 'Apache License 2.0',
    keywords = 'foreman automation',
    url = 'http://github.com/lzoubek/uberforeman',
    install_requires=['requests>=1.2.0'],
    data_files = [],
    package_data = {'': ['*.txt',
                         'examples/*.py',
                         'examples/*/*.py']},
    classifiers = [
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        ],
    **addl_args
    )

