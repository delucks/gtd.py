from setuptools import setup
import sys

sys.path.extend('.')
from todo import __version__

with open('requirements.txt') as f:
    reqs = [l.strip() for l in f]

with open('README.rst') as f:
    readme_contents = f.read()

setup(
    name='mello',
    description='A Fast Command-line Interface for Trello',
    long_description=readme_contents,
    version=__version__,
    install_requires=reqs,
    packages=['todo'],
    py_modules=['mello'],
    entry_points={
        'console_scripts': [
            'mello = mello:main'
        ]
    },
    python_requires='>=3',
    author = 'David Baldwynn',
    author_email = 'david@countable.ca',
    license='BSD 3-clause',
    url = 'https://github.com/whitef0x0/gtd.py',
    download_url = 'https://github.com/whitef0x0/gtd.py/tarball/{}'.format(__version__),
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
