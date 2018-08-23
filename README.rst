gtd.py
=======

A Fast Command-line Interface for Trello
---------------------------------------

This is a command-line tool that enables you to add, sort, and review cards on Trello rapidly. It is designed to reduce the amount of friction between your thoughts and your TODO list, especially if you never leave the terminal.

The project is named "gtd.py" because it was initially built as a tool for me to maintain a Trello board using the GTD_ task tracking method. I've been actively using this tool for GTD since the first commit; if you're trying to use GTD with Trello this is the tool for you.


Usage
-----

In the following examples I'll be working with a sample board, that I created like so:

::

   $ gtd add board PublicShowTest
   Added board PublicShowTest
   $ gtd add list 'Weekly Tasks'
   Successfully added list <List Weekly Tasks>!
   $ for task in 'Do dishes' 'Clean bathroom' 'Write some python' 'Eat a sandwich'; do gtd add card "$task"; done
   Successfully added card <Card Do dishes>!
   Successfully added card <Card Clean bathroom>!
   Successfully added card <Card Write some python>!
   Successfully added card <Card Eat a sandwich>!
   $ gtd show cards
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list  | tags | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes         | To Do |      |      |     | 2018-08-23 00:10:52.513000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Clean bathroom    | To Do |      |      |     | 2018-08-23 00:10:55.360000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   | Write some python | To Do |      |      |     | 2018-08-23 00:10:56.477000+00:00 | PublicShowTest | 5b7dfb9051b9466d0da1c2b7 | https://trello.com/c/p4yeGbkk |
   | Eat a sandwich    | To Do |      |      |     | 2018-08-23 00:10:57.614000+00:00 | PublicShowTest | 5b7dfb91b7b7d66dcc7a21b6 | https://trello.com/c/HL9lJKgZ |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+


Looking Around
^^^^^^^^^^^^^^^^

The ``show`` subcommand allows you to view what's on your board right now. Let's take a look around the new board.

::

   $ gtd show lists
   To Do
   Doing
   Done
   Weekly Tasks
   $ gtd show cards
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list  | tags | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes         | To Do |      |      |     | 2018-08-23 00:10:52.513000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Clean bathroom    | To Do |      |      |     | 2018-08-23 00:10:55.360000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   | Write some python | To Do |      |      |     | 2018-08-23 00:10:56.477000+00:00 | PublicShowTest | 5b7dfb9051b9466d0da1c2b7 | https://trello.com/c/p4yeGbkk |
   | Eat a sandwich    | To Do |      |      |     | 2018-08-23 00:10:57.614000+00:00 | PublicShowTest | 5b7dfb91b7b7d66dcc7a21b6 | https://trello.com/c/HL9lJKgZ |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+


The ``show cards`` command will return all the cards which match your supplied arguments as a table, in JSON format, or in TSV.

::

   # Show cards from the list "Inbox" matching a regular expression on their titles
   $ gtd show cards -l Inbox -m 'https?'
   # Show cards which have no tags but have due dates, in pretty-printed JSON format
   $ gtd show cards --no-tags --has-due -j


Similarly, ``grep`` does what you would expect:

::

   $ gtd grep dishes
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list  | tags | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes         | To Do |      |      |     | 2018-08-23 00:10:52.513000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   +-------------------+-------+------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+

It also faithfully implements some flags from GNU ``grep``, including -c, -i, and -e! An invocation of this command is similar to a longer invocation of ``show``: ``gtd grep 'some_pattern'`` is equivalent to ``gtd show cards -m 'some_pattern'``.

::

   # Filter all cards based on a regex
   $ gtd grep 'http.*amazon'
   # or multiple regexes!
   $ gtd grep -e '[Jj]ob' -e 'career' -e '[oO]pportunity?'
   # Use other popular grep flags!
   $ gtd grep -ci 'meeting'

Creating Things
^^^^^^^^^^^^^^^^

``add`` takes care of your needs for creating new:

* Cards
* Tags
* Lists
* Boards

The ``add tag``, ``add list``, and ``add board`` subcommands all work pretty much the same way.

::

   $ gtd add tag 'Household'
   Successfully added tag <Label Household>!
   $ gtd add tag 'Food'
   Successfully added tag <Label Food>!
   $ gtd add tag 'Programming'
   Successfully added tag <Label Programming>!


The command you'll probably use most frequently is ``add card``.

::

   $ gtd add card 'Purchase a pomelo'
   Successfully added card <Card Purchase a pomelo>!

You can also specify a description for the new card with ``-m``. New cards are put in the first list by default, so when you're laying out a board, make your first list the "inbox". You can also omit the title argument, like so:

::

   # Open $EDITOR so you can write the card title
   $ gtd add card
   Successfully added card <Card This was written in vim>!


Manipulating Cards in Bulk
^^^^^^^^^^^^^^^^^^^^^^^^^^

Frequently it's useful to move a whole bunch of cards at once, tag cards that match a certain parameter, or do other single actions repeatedly across a bunch of cards. To accomplish this, use the ``batch`` command. All the subcommands of ``batch`` are interactive, so you'll be prompted before anything is modified.

::

   $ gtd batch tag -l 'To Do'
   Card 5b7dfb8c5973738e1ed125ab
     Name:         Do dishes
     List:         To Do
     Created:      2018-08-22 20:10:52 (1534983052.0)
     Age:          0:02:04.641306
   Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit
   tag > Household
   Added tag Household
   tag >
   Card 5b7dfb8fed823c431514804d
     Name:         Clean bathroom
     List:         To Do
     Created:      2018-08-22 20:10:55 (1534983055.0)
     Age:          0:02:08.795000
   Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit
   tag > Household
   Added tag Household
   tag >
   Card 5b7dfb9051b9466d0da1c2b7
     Name:         Write some python
     List:         To Do
     Created:      2018-08-22 20:10:56 (1534983056.0)
     Age:          0:02:11.258759
   Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit
   tag >
   tag > Programming
   Added tag Programming
   tag >
   Card 5b7dfb91b7b7d66dcc7a21b6
     Name:         Eat a sandwich
     List:         To Do
     Created:      2018-08-22 20:10:57 (1534983057.0)
     Age:          0:02:13.094361
   Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit
   tag > Food
   Added tag Food
   tag > ^C
   Exiting...
   $

A few things there - the tag names are auto-completed on a python-prompt-toolkit interactive prompt that's case insensitive. Moving from one card to the next in this context happens with Enter, for speed of use reasons. Getting out of the interface was done with Control+C.
Let's put together this ``batch`` knowledge with some stuff we've seen already...

::

   $ gtd add tag 'Shopping'
   Successfully added tag <Label Shopping>!
   $ gtd batch tag --no-tags
   Card 5b7dfc27faa4645e373e9e59
     Name:         Purchase a pomelo
     List:         To Do
     Created:      2018-08-22 20:13:27 (1534983207.0)
     Age:          0:00:15.705034
   Enter a tag name to toggle it, <TAB> completes. Give "ls" to list tags, Enter to exit
   tag > Shopping
   Added tag Shopping
   tag >
   $ gtd show cards -l 'To Do'
   +-------------------+-------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list  | tags        | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+-------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes         | To Do | Household   |      |     | 2018-08-23 00:13:01.438000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Clean bathroom    | To Do | Household   |      |     | 2018-08-23 00:13:06.606000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   | Write some python | To Do | Programming |      |     | 2018-08-23 00:13:09.352000+00:00 | PublicShowTest | 5b7dfb9051b9466d0da1c2b7 | https://trello.com/c/p4yeGbkk |
   | Eat a sandwich    | To Do | Food        |      |     | 2018-08-23 00:13:11.972000+00:00 | PublicShowTest | 5b7dfb91b7b7d66dcc7a21b6 | https://trello.com/c/HL9lJKgZ |
   | Purchase a pomelo | To Do | Shopping    |      |     | 2018-08-23 00:13:47.890000+00:00 | PublicShowTest | 5b7dfc27faa4645e373e9e59 | https://trello.com/c/i7yvMTgD |
   +-------------------+-------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+

Now we've tagged all those new cards in very few keystrokes! Let's move them to more appropriate lists based on their status.

::

   $ gtd batch move -l 'To Do'
   Card 5b7dfb8c5973738e1ed125ab
     Name:         Do dishes
     List:         To Do
     Tags:         Household
     Created:      2018-08-22 20:10:52 (1534983052.0)
     Age:          0:03:41.454345
   Want to move this one? (Y/n)
   [a] Doing
   [s] Done
   [d] To Do
   [f] Weekly Tasks
   Press the character corresponding to your choice, selection will happen immediately. Enter to cancel
   Moved to Doing
   Card 5b7dfb8fed823c431514804d
     Name:         Clean bathroom
     List:         To Do
     Tags:         Household
     Created:      2018-08-22 20:10:55 (1534983055.0)
     Age:          0:03:44.269575
   Want to move this one? (Y/n)
   [a] Doing
   [s] Done
   [d] To Do
   [f] Weekly Tasks
   Press the character corresponding to your choice, selection will happen immediately. Enter to cancel
   Moved to Weekly Tasks
   Card 5b7dfb9051b9466d0da1c2b7
     Name:         Write some python
     List:         To Do
     Tags:         Programming
     Created:      2018-08-22 20:10:56 (1534983056.0)
     Age:          0:03:46.857946
   Want to move this one? (Y/n)
   [a] Doing
   [s] Done
   [d] To Do
   [f] Weekly Tasks
   Press the character corresponding to your choice, selection will happen immediately. Enter to cancel
   Moved to Doing
   Card 5b7dfb91b7b7d66dcc7a21b6
     Name:         Eat a sandwich
     List:         To Do
     Tags:         Food
     Created:      2018-08-22 20:10:57 (1534983057.0)
     Age:          0:03:50.235275
   Want to move this one? (Y/n)
   [a] Doing
   [s] Done
   [d] To Do
   [f] Weekly Tasks
   Press the character corresponding to your choice, selection will happen immediately. Enter to cancel
   Moved to Done
   Card 5b7dfc27faa4645e373e9e59
     Name:         Purchase a pomelo
     List:         To Do
     Tags:         Shopping
     Created:      2018-08-22 20:13:27 (1534983207.0)
     Age:          0:01:24.753457
   Want to move this one? (Y/n)
   [a] Doing
   [s] Done
   [d] To Do
   [f] Weekly Tasks
   Press the character corresponding to your choice, selection will happen immediately. Enter to cancel
   Moved to To Do
   $

Here are some more ideas for you to play with:

::

   # Find all cards with a URL in their title and move those URLs into their attachments
   $ gtd batch attach
   # Set the due dates for all cards in a list containing the substring "Week"
   $ gtd batch due -l Week
   # Change the due date for all cards that have one already
   $ gtd batch due --has-due


Bringing It all Together
^^^^^^^^^^^^^^^^^^^^^^^^

What if you don't know what kind of action you want to take on a card before you invoke ``gtd``? Well, we provide a nice menu for you to work on each card in turn. The menu is kinda REPL-like so if you're a terminal power user (truly, why would you use this tool unless you're already a terminal power-user) it'll feel familiar. The menu is built using ``python-prompt-toolkit`` so it has nice tab-completion on every command available within it. You can type ``help`` at any time to view all the commands available within the REPL. If you get lost, use the ``help`` REPL command.

::

   $ gtd review -l Doing
   Card 5b7dfb8c5973738e1ed125ab
     Name:         Do dishes
     List:         Doing
     Tags:         Household
     Created:      2018-08-22 20:10:52 (1534983052.0)
     Age:          0:05:07.735033
   gtd.py > description
   # Editor session here
   Description changed!
   gtd.py > next
   Card 5b7dfb9051b9466d0da1c2b7
     Name:         Write some python
     List:         Doing
     Tags:         Programming
     Created:      2018-08-22 20:10:56 (1534983056.0)
     Age:          0:05:22.404917
   gtd.py > duedate
   Enter a date in format "Jun 15 2018", "06/15/2018" or "15/06/2018"
   date > Aug 30 2018
   Due date set
   gtd.py > print
   Card 5b7dfb9051b9466d0da1c2b7
     Name:         Write some python
     List:         Doing
     Tags:         Programming
     Created:      2018-08-22 20:10:56 (1534983056.0)
     Age:          0:05:48.787922
     Due:          2018-08-30 04:00:00+00:00
     Remaining:    7 days, 3:43:15.067634
   gtd.py > next
   All done, have a great day!
   $


Deleting Things
^^^^^^^^^^^^^^^

The ``delete`` subcommand allows you to get rid of lists & cards. By default, cards are archived rather than deleted. You can override this behavior with the ``-f/--force`` flag to ``delete cards``. Lists may not be deleted, so they are archived when you run ``delete list``.

::

   $ gtd add card 'cannon fodder'
   Successfully added card <Card cannon fodder>!
   $ gtd delete cards -m cannon
   Card 5b7e061d94997510c6ee0ce9
     Name:         cannon fodder
     List:         Weekly Tasks
     Created:      2018-08-22 20:55:57 (1534985757.0)
     Age:          0:00:14.543394
   Delete this card? (y/N) y
   Card archived!
   $

Here are some other examples of ``delete``:

::

   # Delete without intervention all cards containing the string "testblah"
   $ gtd delete cards --noninteractive --force -m 'testblah'
   # Delete the list named "Temporary work"
   $ gtd delete list "Temporary work"

Revisiting ``show``
^^^^^^^^^^^^^^^^^^^

Now that we've added a lot more to our sample board, let's try some more advanced examples of ``show cards``. This command is the most flexible one of the bunch, so definitely try it out for yourself.

::

   $ gtd show cards -t Household
   +----------------+--------------+-----------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name           | list         | tags      | desc | due | last activity                    | board          | id                       | url                           |
   +----------------+--------------+-----------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes      | Doing        | Household |      |     | 2018-08-23 00:14:39.081000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Clean bathroom | Weekly Tasks | Household |      |     | 2018-08-23 00:14:42.663000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   +----------------+--------------+-----------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   $ gtd show cards --by name
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list         | tags        | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Clean bathroom    | Weekly Tasks | Household   |      |     | 2018-08-23 00:14:42.663000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   | Do dishes         | Doing        | Household   |      |     | 2018-08-23 00:14:39.081000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Eat a sandwich    | Done         | Food        |      |     | 2018-08-23 00:14:51.535000+00:00 | PublicShowTest | 5b7dfb91b7b7d66dcc7a21b6 | https://trello.com/c/HL9lJKgZ |
   | Purchase a pomelo | To Do        | Shopping    |      |     | 2018-08-23 00:13:47.890000+00:00 | PublicShowTest | 5b7dfc27faa4645e373e9e59 | https://trello.com/c/i7yvMTgD |
   | Write some python | Doing        | Programming |      |     | 2018-08-23 00:14:47.048000+00:00 | PublicShowTest | 5b7dfb9051b9466d0da1c2b7 | https://trello.com/c/p4yeGbkk |
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   $ gtd show cards --by list
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | name              | list         | tags        | desc | due | last activity                    | board          | id                       | url                           |
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+
   | Do dishes         | Doing        | Household   |      |     | 2018-08-23 00:14:39.081000+00:00 | PublicShowTest | 5b7dfb8c5973738e1ed125ab | https://trello.com/c/DrZ2tFr0 |
   | Write some python | Doing        | Programming |      |     | 2018-08-23 00:14:47.048000+00:00 | PublicShowTest | 5b7dfb9051b9466d0da1c2b7 | https://trello.com/c/p4yeGbkk |
   | Eat a sandwich    | Done         | Food        |      |     | 2018-08-23 00:14:51.535000+00:00 | PublicShowTest | 5b7dfb91b7b7d66dcc7a21b6 | https://trello.com/c/HL9lJKgZ |
   | Purchase a pomelo | To Do        | Shopping    |      |     | 2018-08-23 00:13:47.890000+00:00 | PublicShowTest | 5b7dfc27faa4645e373e9e59 | https://trello.com/c/i7yvMTgD |
   | Clean bathroom    | Weekly Tasks | Household   |      |     | 2018-08-23 00:14:42.663000+00:00 | PublicShowTest | 5b7dfb8fed823c431514804d | https://trello.com/c/QVATaeaH |
   +-------------------+--------------+-------------+------+-----+----------------------------------+----------------+--------------------------+-------------------------------+

You can also filter the fields that are shown with the ``--fields`` argument. By default, ``gtd.py`` will trim down the fields until it fits your current terminal width. It'll only wrap if you have really long card titles relative to the width of your terminal.


Setup
------

::

  $ pip install gtd.py
  $ gtd onboard

The ``onboard`` command will assist you through the process of getting a Trello API key for use with this program and putting it in the correct file. This will happen automatically if you run a command that requires authentication without having your API keys set.

If you'd like to enable automatic bash completion for gtd.py, add the following line to your ~/.bashrc:

::

  eval "$(_GTD_COMPLETE=source gtd)"

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
  banner: True  # Do you want to see the "gtd.py" banner on each program run?


All of these can be overridden on the command-line with the ``-b``, ``--no-color``, and ``--no-banner`` flags. All of the above examples were recorded with ``--no-color --no-banner``.

This configuration file can be put in a variety of locations within your home folder. The ``onboard`` command will help you with platform detection, putting the configuration file where appropriate given your operating system. When running, ``gtd``` will check all possible locations out of this list:

* ``~/.gtd.yaml``
* ``~/.config/gtd/gtd.yaml``
* ``~/Library/Application Support/gtd/gtd.yaml``
* ``~/.local/etc/gtd.yaml``
* ``~/.local/etc/gtd/gtd.yaml``

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
