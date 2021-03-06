from setuptools import setup
import sys

sys.path.extend('.')
from todo import __version__

test_require = ['flake8', 'black', 'pytest']

with open('requirements.txt') as f:
    reqs = [l.strip() for l in f if not any(l.startswith(t) for t in test_require)]

with open('README.rst') as f:
    readme_contents = f.read()

setup(
    name='gtd.py',
    description='A Fast Command-line Interface for Trello',
    long_description=readme_contents,
    version=__version__,
    install_requires=reqs,
    test_requires=test_require,
    packages=['todo'],
    py_modules=['gtd'],
    entry_points={
        'console_scripts': [
            'gtd = gtd:main'
        ]
    },
    python_requires='>=3.8',
    author='James Luck',
    author_email='me@jamesluck.com',
    license='BSD 3-clause',
    url='https://github.com/delucks/gtd.py',
    download_url=f'https://github.com/delucks/gtd.py/tarball/{__version__}',
    keywords=['productivity', 'cli', 'trello', 'gtd', 'getting things done'],
    classifiers=[
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
