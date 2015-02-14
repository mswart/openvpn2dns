from setuptools import setup  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

if not path.exists(path.join(here, 'README.rst')):
    try:
        import subprocess
        subprocess.call(['pandoc',
                         '--from=markdown', '--to=rst',
                         path.join(here, 'README.md'),
                         '--output', path.join(here, 'README.rst')])
    except:
        import os
        os.copy(path.join(here, 'README.md'), path.join(here, 'README.rst'))

# Get the long description from the relevant file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

import version


setup(
    name='openvpn2dns',
    version=version.STRING,

    description='DNS server in python serving openvpn status files as dns zones',
    long_description=long_description,

    url='https://github.com/mswart/openvpn2dns',

    author='Malte Swart',
    author_email='mswart@devtation.de',

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: System Administrators',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: System :: Networking',
        'Topic :: Communications',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='openvpn twisted dns',

    install_requires=[
        #'Twisted >= 10', diabled as only twisted-names is needed
        'IPy >= 0.73'
    ],
    py_modules=('config', 'openvpnzone', 'version'),
    scripts=('openvpn2dns', )
)
