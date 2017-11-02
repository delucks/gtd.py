from setuptools import setup
import sys

sys.path.extend('.')
from todo import __version__

with open('requirements.txt') as f:
    reqs = [l.strip() for l in f]

setup(
    name='gtd.py',
    version=__version__,
    install_requires=reqs,
    packages=['todo'],
    entry_points={
        'console_scripts': [
            'gtd = gtd:main'
        ]
    },
    author = 'James Luck',
    author_email = 'me@jamesluck.com',
    license='BSD 3-clause',
    url = 'https://github.com/delucks/gtd.py',
    download_url = 'https://github.com/delucks/gtd.py/tarball/{}'.format(__version__),
    keywords = ['productivity', 'cli', 'trello', 'gtd', 'getting things done'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX :: Linux',
        'Operating System :: POSIX :: BSD',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Utilities'
    ]
)