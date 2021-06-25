#!/bin/python

from setuptools import setup, find_packages

entry_points = {
    "console_scripts": [
        "biomedmap=biomedmap:main",
        "bmm=biomedmap:main"
    ]
}

setup(
    name="biomedmap",
    version='0.4',
    description="",
    packages=find_packages(),
    platforms='any',
    entry_points=entry_points,
    package_data={
        "": [
            "templates/*"
        ]
    }
)
