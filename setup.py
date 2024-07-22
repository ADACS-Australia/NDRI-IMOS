#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages
import re


def get_property(prop, project):
    result = re.search(r'{}\s*=\s*[\'"]([^\'"]*)[\'"]'.format(prop),
                       open(project + '/__init__.py').read())
    return result.group(1)


def get_version():
    """Get the version number of the package"""
    # ## the original inspired by Paul's Aegean package
    # ## does not work with simplified imports trick in __init__.py
    import IMOSPATools
    return IMOSPATools.__version__


with open('README.rst') as readme_file:
    readme = readme_file.read()

# with open('HISTORY.rst') as history_file:
#     history = history_file.read()

# add all libraries
requirements = ["numpy",
                "wave",
                "mutagen",
                "soundfile",
                "matplotlib",
                "scipy"]

package_name = 'IMOSPATools'

setup(
    author=get_property('__author__', package_name),
    author_email=get_property('__email__', package_name),
    name=package_name,
    python_requires='>=3.8.0',
    version=get_property('__version__', package_name),
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    description="IMOS Passive Audio Data Processing Tools",
    install_requires=requirements,
    license="MIT license",
    # long_description=readme + '\n\n' + history,
    long_description=readme,
    include_package_data=True,
    keywords='IMOS ANMN AODN audio hydrophone',
    packages=find_packages(include=[package_name]),
    # package_data={package_name: ['data/*']},
    test_suite='tests',
    url='https://github.com/ADACS-Australia/NDRI-IMOS',
    zip_safe=False,
)
