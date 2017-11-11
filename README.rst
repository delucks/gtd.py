gtd.py
=======

A Fast Command-line Interface for Trello
---------------------------------------

This is a command-line tool that enables you to add, sort, and review cards on Trello rapidly. It is designed to reduce the amount of friction between your thoughts and your TODO list, especially if you never leave the terminal.

The project is named "gtd.py" because it was initially built as a tool for me to maintain a Trello board using the GTD_ task tracking method. I've been actively using this tool for GTD since the first commit; if you're trying to use GTD with Trello this is the tool for you.

Setup
------

::

  $ pip install gtd.py
  $ gtd onboard

The ``onboard`` command will assist you through the process of getting a Trello API key for use with this program and putting it in the correct file. This will happen automatically if you run a command that requires authentication without having your API keys set.


Configuration
--------------

The ``onboard`` command will help you create the configuration file interactively. If you prefer to do the process manually, Trello has a button on their website for temporarily creating an OAUTH key/token. That should be put in a yaml file formatted like this:

::

  api_key: "your-api-key"
  api_secret: "your-api-secret"
  oauth_token: "your-oauth-token"
  oauth_token_secret: "your-oauth-secret"


There are other optional settings you can define inside your yaml configuration file:

::

  board: "Name of the Trello board you want to work with (case sensitive)"
  color: True   # Do you want to show ANSI colors in the terminal?
  banner: True  # Do you want to see the "gtd.py" banner on each program run?


All of these can be overridden on the command-line with the ``-b``, ``--no-color``, and ``--no-banner`` flags.

This configuration file can be put in a variety of locations within your home folder. The ``onboard`` command will help you with platform detection, putting the configuration file where appropriate given your operating system. When running, ``gtd``` will check all possible locations out of this list:

* ``~/.gtd.yaml``
* ``~/.config/gtd/gtd.yaml``
* ``~/Library/Application Support/gtd/gtd.yaml``
* ``~/.local/etc/gtd.yaml``
* ``~/.local/etc/gtd/gtd.yaml``


Usage
-----

Filter & show cards:

::

  # Show cards from a list matching a regular expression on their titles
  $ gtd show cards -l Inbox -m 'https?'

  # Show cards which have no tags but have due dates
  $ gtd show cards --no-tags --has-due

  # Filter all cards based on a regex
  $ gtd grep 'http.*amazon'


Notes
------

* The code is not heavily tested. Please (please!) report bugs if you find them.
* This has only been used on Linux and Mac OSX
* Windows is not supported.
* Some naming conventions differ from Trello, most notably "label" is called "tag"

License
--------

BSD. There is a copy included with the software as LICENSE.txt

Copyright 2017 Jamie Luck (delucks)


.. _GTD: https://en.wikipedia.org/wiki/Getting_Things_Done
