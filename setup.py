try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='PyRMVtransport',
    version='0.0.1',
    description='get transport information from opendata.rmv.de',
    author='cgtobi',
    author_email='cgtobi@gmail.com',
    url='https://github.com/cgtobi/PyRMVtransport',
    packages=['RMVtransport'],
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords='',
    license='?',
    install_requires=['lxml'],
)
