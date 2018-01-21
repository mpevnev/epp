from setuptools import setup, find_packages

setup(
    name="epp",
    version="0.1",
    package_dir={"": "src"},
    packages=find_packages("src/epp"),

    test_suite="test",

    author="Michail Pevnev",
    author_email="mpevnev@gmail.com",
    description="Effectful pythonic parsers",
    license="GPL-3",
    keywords="parser parsers",
    url="https://github.com/mpevnev/epp",
)
