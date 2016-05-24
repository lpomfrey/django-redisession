#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
from setuptools import setup, find_packages


def get_version(package):
    '''
    Return package version as listed in `__version__` in `init.py`.
    '''
    init_py = open(os.path.join(package, '__init__.py')).read()
    return re.search(
        '^__version__ = [\'"]([^\'"]+)[\'"]', init_py, re.MULTILINE
    ).group(1)


version = get_version('redisession')


if sys.argv[-1] == 'publish':
    os.system('python setup.py sdist upload')
    os.system('python setup.py bdist_wheel upload')
    args = {'version': version}
    print('You probably want to also tag the version now:')
    print(' git tag -a {version} -m \'version {version}\''.format(
        **args))
    print(' git push --tags')
    sys.exit()


setup(
    name='django-redisession-ng',
    version=version,
    license='MIT',
    author='Li Meng',
    author_email='liokmkoil@gmail.com',
    maintainer='Luke Pomfrey',
    maintainer_email='lpomfrey@gmail.com',
    packages=find_packages(exclude=('test_project', 'docs')),
    description=(
        'A Redis-based Django session engine for django.contrib.sessions.'
    ),
    long_description=open('README.rst').read(),
    url='https://github.com/lpomfrey/django-redisession',
    download_url='https://github.com/lpomfrey/django-redisession',
    install_requires=[
        'redis',
    ],
    tests_require=[
        'django',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Framework :: Django',
        'Framework :: Django :: 1.8',
        'Framework :: Django :: 1.9',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Topic :: Internet :: WWW/HTTP'
    ]
)
