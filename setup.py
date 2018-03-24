from setuptools import setup, find_packages

from os import path

def long_description():
    """ Read the descrption from README. """
    here = path.abspath(path.dirname(__file__))
    with open(path.join(here, "README.rst")) as f:
        return f.read()

setup(
    name="epparsers",
    version="0.4.1",
    package_dir={"": "src"},
    packages=find_packages("src"),

    test_suite="test",

    author="Michail Pevnev",
    author_email="mpevnev@gmail.com",
    description="Effectful pythonic parsers",
    long_description=long_description(),
    license="LGPL-3",
    keywords="parser parsers",
    url="https://github.com/mpevnev/epp",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)"
        ]
)
