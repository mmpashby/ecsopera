from ecsopera.version import __version__
from setuptools import setup, find_packages

setup(name='ecsopera',
      version=__version__,
      description='Elastic Container Orchestrator Toolset.',
      url='http://github.com/Pashbee/ecsopera',
      author='Pashbee',
      license='MIT',
      packages=find_packages(exclude=['tests']),
      include_package_data=True,
      install_requires=['click', 'boto3', 'moto', 'progressbar2', 'pytest'],
      zip_safe=False,
      entry_points={
        'console_scripts': [
            'ecsopera = ecsopera.cli:ecsopera',
        ],
      },
      classifiers=[
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Operating System :: MacOS',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
])
