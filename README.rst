Mello
=======

A Fast Command-line Interface for Trello
---------------------------------------

This is a command-line tool that enables you to add, sort, and review cards on Trello rapidly. It is designed to reduce the amount of friction between your thoughts and your TODO list, especially if you never leave the terminal.

Installation
------------

When installing, make sure to use pip3 if you your machine defaults to python2.7
1. Install via pip
`pip3 install mello`

1.1 (Optional) Add python3 bin to PATH if you haven't already done so

2. Setup OAuth credentials
`mello reconfigure`


Usage
-----

Displaying Unresponded Comments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``show unresponded`` command will return all comments that mention your username that you have not responded to yet.

Displaying Cards
^^^^^^^^^^^^^^^^

The ``show`` command will return all the cards which match your supplied arguments as a table, in JSON format, or in TSV.

::

  # Show cards from the list "Inbox" matching a regular expression on their titles
  $ mello show cards -l Inbox -m 'https?'

  # Show cards which have no tags but have due dates, in pretty-printed JSON format
  $ mello show cards --no-tags --has-due -j


``grep`` faithfully implements some flags from the venerable utility, including -c, -i, and -e! An invocation of this command is similar to a longer invocation of ``show``: ``mello grep 'some_pattern'`` is equivalent to ``mello show cards -m 'some_pattern'``.

::

  # Filter all cards based on a regex
  $ mello grep 'http.*amazon'

  # or multiple regexes!
  $ mello grep -e '[Jj]ob' -e 'career' -e '[oO]pportunity?'

  # Use other popular grep flags!
  $ mello grep -ci 'meeting'

Creating Things
^^^^^^^^^^^^^^^^

``add`` takes care of your needs for creating new:

* Cards
* Tags
* Lists

The command you'll probably use most frequently is ``add card``. Here are some common ways I use it:

::

  # Add a new card with title "foo"
  $ mello add card foo

  # Specify a description with the card title
  $ mello add card foo -m 'Description for my new card'

  # Open $EDITOR so you can write the card title
  $ mello add card

The other subcommands for ``add`` (``add list`` and ``add tag``) are self-explanatory.

Deleting Things
^^^^^^^^^^^^^^^

The ``delete`` subcommand allows you to get rid of lists & cards. By default, cards are archived rather than deleted. You can override this behavior with the ``-f/--force`` flag to ``delete cards``. Lists may not be deleted, so they are archived when you run ``delete list``.

::

  # Archive all cards whose titles match this regular expression
  $ mello delete cards -m 'on T(hurs|ues)day'

  # Delete without intervention all cards containing the string "testblah"
  $ mello delete cards --noninteractive --force -m 'testblah'

  # Delete the list named "Temporary work"
  $ mello delete list "Temporary work"


Manipulating Cards in Bulk
^^^^^^^^^^^^^^^^^^^^^^^^^^

Frequently it's useful to move a whole bunch of cards at once, tag cards that match a certain parameter, or do other single actions repeatedly across a bunch of cards. To accomplish this, use the ``batch`` command. All the subcommands of ``batch`` are interactive, so you'll be prompted before anything is modified.

::

  # Tag all cards that have no tags
  $ mello batch tag --no-tags

  # Find all cards with a URL in their title and move those URLs into their attachments
  $ mello batch attach

  # Move all cards in your "Inbox" list
  $ mello batch move -l Inbox

  # Set the due dates for all cards in a list containing the substring "Week"
  $ mello batch due -l Week

  # Change the due date for all cards that have one already
  $ mello batch due --has-due


Bringing It all Together
^^^^^^^^^^^^^^^^^^^^^^^^

What if you don't know what kind of action you want to take on a card before you invoke ``mello``? Well, we provide a nice menu for you to work on each card in turn. The menu is kinda REPL-like so if you're a terminal power user (truly, why would you use this tool unless you're already a terminal power-user) it'll feel familiar. The menu is built using ``python-prompt-toolkit`` so it has nice tab-completion on every command available within it. You can type ``help`` at any time to view all the commands available within the REPL.

Seeing is believing, so until I record a terminal session of me using it I'd highly encourage you to play around with this menu. It does some detection on the title of your card and will prompt you to move links out into attachments if appropriate. If the card doesn't have any tags yet, it'll prompt you to add some.

::

  # Work through cards in the "Inbox" list one at a time
  $ mello review -l Inbox

  # Review only cards from the "Today" list that have due dates
  $ mello review -l Today --has-due


Setup
------

::

  $ pip install mello.py
  $ mello onboard

The ``onboard`` command will assist you through the process of getting a Trello API key for use with this program and putting it in the correct file. This will happen automatically if you run a command that requires authentication without having your API keys set.

If you'd like to enable automatic bash completion for mello.py, add the following line to your ~/.bashrc:

::

  eval "$(_GTD_COMPLETE=source mello)"

This relies on ``click``'s internal bash completion engine, so it does not work on other shells like ``sh``, ``csh``, or ``zsh``.

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
  banner: True  # Do you want to see the "mello.py" banner on each program run?


All of these can be overridden on the command-line with the ``-b``, ``--no-color``, and ``--no-banner`` flags.

This configuration file can be put in a variety of locations within your home folder. The ``onboard`` command will help you with platform detection, putting the configuration file where appropriate given your operating system. When running, ``mello``` will check all possible locations out of this list:

* ``~/.mello.yaml``
* ``~/.config/mello/mello.yaml``
* ``~/Library/Application Support/mello/mello.yaml``
* ``~/.local/etc/mello.yaml``
* ``~/.local/etc/mello/mello.yaml``

Notes
------

* The code is manually tested. Please (please!) report bugs if you find them.
* This has only been used on Linux and Mac OSX
* Windows is not supported.
* Some naming conventions differ from Trello, most notably "label" is called "tag"

License
--------

BSD. There is a copy included with the software as LICENSE

Copyright 2018 Jamie Luck (delucks)


.. _GTD: https://en.wikipedia.org/wiki/Getting_Things_Done
