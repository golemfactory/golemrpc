from setuptools import setup, find_packages

import os

libdir = os.path.dirname(os.path.realpath(__file__))
req_path = os.path.join(
    libdir,
    'requirements.txt'
)

with open(req_path, 'r') as f:
    install_requires = list(f.read().splitlines())

setup(name='golemrpc',
      version='0.3.4',
      description='Golem RPC library',
      url='http://github.com/golemfactory/raspa-poc',
      author='Golem Team',
      author_email='contact@golem.network',
      license='MIT',
      packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*", "tests"]),
      install_requires=install_requires,
      zip_safe=False)
