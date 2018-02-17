from setuptools import setup, find_packages

setup(
    name="epparsers",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages("src"),

    test_suite="test",

    author="Michail Pevnev",
    author_email="mpevnev@gmail.com",
    description="Effectful pythonic parsers",
    license="LGPL-3",
    keywords="parser parsers",
    url="https://github.com/mpevnev/epp",
)
