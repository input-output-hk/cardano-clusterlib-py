from setuptools import find_packages
from setuptools import setup

setup(
    name="cardano-clusterlib",
    packages=find_packages(),
    setup_requires=["setuptools_scm"],
    use_scm_version=True,
)
