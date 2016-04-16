#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from setuptools import setup, find_packages

try:
    import pypandoc
except ImportError:
    class pypandoc(object):
        @classmethod
        def convert(self, data, type, format):
            return data

__version__ = None
with open('src/lambda_deploy/version.py') as vfp:
    vd = vfp.read().strip()
    __version__ = vd.split('=')[1].strip().strip('\'').strip('"')

readme = open('README.md').read()
history = open('HISTORY.md').read().replace('.. :changelog:', '')
long_description = readme + '\n\n' + history


def get_requirements(filename):
    requirements = []
    if os.path.exists(filename):
        with open(filename) as rfp:
            [
                requirements.append(r.strip())
                for r in rfp if not r.startswith('-')
            ]

    return requirements


requirements = get_requirements('requirements.txt')
setup_requirements = get_requirements('requirements_setup.txt')
test_requirements = get_requirements('requirements_test.txt')


setup(
    name='lambda-deploy',
    version=__version__ if __version__ else 'UNKNOWN',
    description='Easily deploy code to AWS Lambda',
    long_description=pypandoc.convert(long_description, 'rst', format='md'),
    author='James Kelly',
    author_email='pthread1981@gmail.com',
    url='https://github.com/jimjkelly/lambda-deploy',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    include_package_data=True,
    install_requires=requirements,
    setup_requires=setup_requirements,
    tests_require=test_requirements,
    test_suite='nose.collector',
    keywords='aws lambda',
    zip_safe=False,
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Environment :: Console',
        'Programming Language :: Python',
        'Natural Language :: English',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Topic :: System :: Software Distribution',
    ],
    entry_points={
        "console_scripts": ['lambda-deploy = lambda_deploy.lambda_deploy:main']
    },
)
