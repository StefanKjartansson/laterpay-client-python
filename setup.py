# -*- coding: UTF-8 -*-
from setuptools import find_packages, setup

import codecs
import os

#import time
#_version = "3.0.dev%s" % int(time.time())
_version = "3.0.0"
_packages = find_packages('.', exclude=["*.tests", "*.tests.*", "tests.*", "tests"])

if os.path.exists('README.rst'):
    _long_description = codecs.open('README.rst', 'r', 'utf-8').read()
else:
    _long_description = ""

setup(
    name='laterpay-client',
    version=_version,

    description="LaterPay API client",
    long_description=_long_description,
    author="LaterPay GmbH",
    author_email="support@laterpay.net",
    url="https://github.com/laterpay/laterpay-client-python",
    license='MIT',
    keywords="LaterPay API client",

    test_suite="tests",

    packages=_packages,
    package_data={'laterpay.django': ['templates/laterpay/inclusion/*']},

    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ),
)
