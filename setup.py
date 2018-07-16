from ecsopera.version import __version__
from setuptools import setup

setup(name='ecsopera',
      version=__version__,
      description='Elastic Container Orchestrator Toolset.',
      url='http://github.com/Pashbee/ecsopera',
      author='Pashbee',
      license='MIT',
      packages=['ecsopera'],
      install_requires=['click', 'boto3', 'moto', 'progressbar2', 'pytest'],
      scripts=['bin/ecsopera'],
      zip_safe=False)
