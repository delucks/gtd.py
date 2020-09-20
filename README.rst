gtd.py
=======

A Fast Command-line Interface for Trello
----------------------------------------

This is a command-line tool that enables you to add, sort, and review cards on Trello rapidly. It is designed to reduce the amount of friction between your thoughts and your TODO list. If you never leave the terminal, gtd.py will feel right at home. It has tab-completion throughout, machine-readable ``--json`` and ``--tsv`` flags, a ``grep`` subcommand, and an interactive REPL mode.

The project is named "gtd.py" because it was initially built as a tool to maintain a Trello board using the GTD_ task tracking method. I've been actively using this tool for GTD since the first commit; if you're trying to use GTD with Trello this is the tool for you.

.. image:: ./demo.svg
   :alt: Animated Demonstration

Usage
-----

In the following examples I'll be working with a sample board, that I created like so:

::

  $ gtd add board PublicShowTest
  Added board PublicShowTest
  $ echo "board: PublicShowTest" >> ~/.config/gtd/gtd.yaml
  $ gtd add list 'To Do'
  Successfully added list <List To Do>!
  $ gtd add list 'Weekly Tasks'
  Successfully added list <List Weekly Tasks>!
  $ for task in 'Do dishes' 'Clean bathroom' 'Write some python' 'Eat a sandwich'; do gtd add card "$task"; done
  Successfully added card "Do dishes"!
  Successfully added card "Clean bathroom"!
  Successfully added card "Write some python"!
  Successfully added card "Eat a sandwich"!


Looking Around
^^^^^^^^^^^^^^^^

The ``show`` subcommand allows you to view what's on your board right now. Let's take a look around the new board.

::

  $ gtd show lists
  Weekly Tasks (5f679dbc195e7885699ceb64)
  To Do (5f679d625b4bbd1a91878fb8)
  Doing (5f679d625b4bbd1a91878fb9)
  Done (5f679d625b4bbd1a91878fba)
  $ gtd show cards
  Fetching cards  [########################################################################################################]  100%
  +-------------------+--------------+------+------+-----+------------+--------------------------+-------------------------------+
  | name              | list         | tags | desc | due | activity   | id                       | url                           |
  +-------------------+--------------+------+------+-----+------------+--------------------------+-------------------------------+
  | Clean bathroom    | Weekly Tasks |      |      |     | 2020-09-20 | 5f679de5b92a1708bd7c8c93 | https://trello.com/c/ds3tuegh |
  | Do dishes         | Weekly Tasks |      |      |     | 2020-09-20 | 5f679de3b9c40b795bd6e08b | https://trello.com/c/8qBVAraN |
  | Eat a sandwich    | Weekly Tasks |      |      |     | 2020-09-20 | 5f679de818062617023a4405 | https://trello.com/c/o5Oph6AD |
  | Write some python | Weekly Tasks |      |      |     | 2020-09-20 | 5f679de74d9e0e69f717686f | https://trello.com/c/fflo7zzp |
  +-------------------+--------------+------+------+-----+------------+--------------------------+-------------------------------+


The ``show cards`` command will return all the cards which match your supplied arguments as a table, in JSON format, or in TSV.

::

  # Show cards from the list "Inbox" matching a regular expression on their titles
  $ gtd show cards -l Inbox --match 'https?'
  # Show cards which have no tags but have due dates, in pretty-printed JSON format
  $ gtd show cards --no-tags --has-due --json
  # Closed cards which have attachments and are tagged as "Pictures"
  $ gtd show cards --status closed --attachments -t Pictures


Similarly, ``grep`` does what you would expect:

::

  $ gtd grep dishes
  +-----------+--------------+------+------+-----+------------+--------------------------+-------------------------------+
  | name      | list         | tags | desc | due | activity   | id                       | url                           |
  +-----------+--------------+------+------+-----+------------+--------------------------+-------------------------------+
  | Do dishes | Weekly Tasks |      |      |     | 2020-09-20 | 5f679de3b9c40b795bd6e08b | https://trello.com/c/8qBVAraN |
  +-----------+--------------+------+------+-----+------------+--------------------------+-------------------------------+

It also faithfully implements some flags from GNU ``grep``, including -c, -i, and -e! An invocation of this command is similar to a longer invocation of ``show``: ``gtd grep 'some_pattern'`` is equivalent to ``gtd show cards -m 'some_pattern'``.

::

  # Filter all cards based on a regex
  $ gtd grep 'http.*amazon'
  # or multiple regexes!
  $ gtd grep -e '[Jj]ob' -e 'career' -e '[oO]pportunity?'
  # Count matches of a case-insensitive pattern
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

  $ for tag in Household Food Programming; do gtd add tag "$tag"; done
  Created tag "Household"
  Created tag "Food"
  Created tag "Programming"


The command you'll probably use most frequently is ``add card``.

::

  $ gtd add card 'Purchase a pomelo'
  Successfully added card "Purchase a pomelo"!

You can also specify a description for the new card with ``-m``. New cards are put in the first list by default, so when you're laying out a board, make your first list the "inbox". You can also omit the title argument, like so:

::

  # Open $EDITOR so you can write the card title
  $ gtd add card
  Successfully added card "This was written in vim"!


Manipulating Cards in Bulk
^^^^^^^^^^^^^^^^^^^^^^^^^^

Frequently it's useful to move a whole bunch of cards at once, tag cards that match a certain parameter, or do other single actions repeatedly across a bunch of cards. To accomplish this, use the ``batch`` command. All the subcommands of ``batch`` are interactive, so you'll be prompted before anything is modified.

::

  $ gtd batch tag -l 'Weekly Tasks'
  Card 5f679de3b9c40b795bd6e08b
    Name:         Do dishes
    List:         Weekly Tasks
    Created:      2020-09-20 14:22:27 (1600626147)
    Age:          0:12:18.823795
  Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit
  gtd.py > tag > Household
  Added tag Household
  gtd.py > tag >
  Card 5f679de5b92a1708bd7c8c93
    Name:         Clean bathroom
    List:         Weekly Tasks
    Created:      2020-09-20 14:22:29 (1600626149)
    Age:          0:12:31.717111
  Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit
  gtd.py > tag > Household
  Added tag Household
  gtd.py > tag >
  Card 5f679de74d9e0e69f717686f
    Name:         Write some python
    List:         Weekly Tasks
    Created:      2020-09-20 14:22:31 (1600626151)
    Age:          0:12:43.708735
  Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit
  gtd.py > tag > Programming
  Added tag Programming
  gtd.py > tag >
  Card 5f679de818062617023a4405
    Name:         Eat a sandwich
    List:         Weekly Tasks
    Created:      2020-09-20 14:22:32 (1600626152)
    Age:          0:12:46.228887
  Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit
  gtd.py > tag > Food
  Added tag Food
  gtd.py > tag >

A few things there - the tag names are fuzzy matched on a python-prompt-toolkit interactive prompt that's case insensitive. Moving from one card to the next in this context happens with Ctrl+D, a convention that's used throughout the nested menu system. Getting out of the interface is done with Control+C.
Let's put together this ``batch`` knowledge with some stuff we've seen already...

::

  $ gtd add tag 'Shopping'
  Created tag "Shopping"
  $ gtd batch tag --no-tags
  Card 5f679ff8f48c48484a2809db
    Name:         Purchase a pomelo
    List:         Weekly Tasks
    Created:      2020-09-20 14:31:20 (1600626680)
    Age:          0:10:00.322370
  Enter a tag name to toggle it, <TAB> completes. Ctrl+D to exit
  gtd.py > tag > Food
  Added tag Food
  gtd.py > tag >
  $ gtd show cards -l 'Weekly Tasks'
  +-------------------------+--------------+-------------+------+-----+------------+--------------------------+-------------------------------+
  | name                    | list         | tags        | desc | due | activity   | id                       | url                           |
  +-------------------------+--------------+-------------+------+-----+------------+--------------------------+-------------------------------+
  | Clean bathroom          | Weekly Tasks | Household   |      |     | 2020-09-20 | 5f679de5b92a1708bd7c8c93 | https://trello.com/c/ds3tuegh |
  | Do dishes               | Weekly Tasks | Household   |      |     | 2020-09-20 | 5f679de3b9c40b795bd6e08b | https://trello.com/c/8qBVAraN |
  | Eat a sandwich          | Weekly Tasks | Food        |      |     | 2020-09-20 | 5f679de818062617023a4405 | https://trello.com/c/o5Oph6AD |
  | Purchase a pomelo       | Weekly Tasks | Food        |      |     | 2020-09-20 | 5f679ff8f48c48484a2809db | https://trello.com/c/K6N4ilHZ |
  | This was written in vim | Weekly Tasks | Programming |      |     | 2020-09-20 | 5f67a0180ce40186bbff7cf6 | https://trello.com/c/o8vucw6f |
  | Write some python       | Weekly Tasks | Programming |      |     | 2020-09-20 | 5f679de74d9e0e69f717686f | https://trello.com/c/fflo7zzp |
  +-------------------------+--------------+-------------+------+-----+------------+--------------------------+-------------------------------+

Now we've tagged all those new cards in very few keystrokes! Let's move them to more appropriate lists based on their status.

::

  $ gtd batch move -l 'Weekly Tasks'
  Card 5f679de3b9c40b795bd6e08b
    Name:         Do dishes
    List:         Weekly Tasks
    Tags:         Household
    Created:      2020-09-20 14:22:27 (1600626147)
    Age:          0:21:53.605262
  Want to move this one? (Y/n)
  [a] Doing
  [s] Done
  [d] To Do
  [f] Weekly Tasks
  Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel
  Moved to To Do
  Card 5f679de5b92a1708bd7c8c93
    Name:         Clean bathroom
    List:         Weekly Tasks
    Tags:         Household
    Created:      2020-09-20 14:22:29 (1600626149)
    Age:          0:21:57.033431
  Want to move this one? (Y/n)
  Card 5f679de74d9e0e69f717686f
    Name:         Write some python
    List:         Weekly Tasks
    Tags:         Programming
    Created:      2020-09-20 14:22:31 (1600626151)
    Age:          0:21:59.924228
  Want to move this one? (Y/n)
  [a] Doing
  [s] Done
  [d] To Do
  [f] Weekly Tasks
  Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel
  Moved to To Do
  Card 5f679de818062617023a4405
    Name:         Eat a sandwich
    List:         Weekly Tasks
    Tags:         Food
    Created:      2020-09-20 14:22:32 (1600626152)
    Age:          0:22:04.439588
  Want to move this one? (Y/n)
  [a] Doing
  [s] Done
  [d] To Do
  [f] Weekly Tasks
  Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel
  Moved to Doing
  Card 5f679ff8f48c48484a2809db
    Name:         Purchase a pomelo
    List:         Weekly Tasks
    Tags:         Food
    Created:      2020-09-20 14:31:20 (1600626680)
    Age:          0:13:25.517654
  Want to move this one? (Y/n)
  [a] Doing
  [s] Done
  [d] To Do
  [f] Weekly Tasks
  Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel
  Moved to To Do
  Card 5f67a0180ce40186bbff7cf6
    Name:         This was written in vim
    List:         Weekly Tasks
    Tags:         Programming
    Created:      2020-09-20 14:31:52 (1600626712)
    Age:          0:12:57.808064
  Want to move this one? (Y/n)
  [a] Doing
  [s] Done
  [d] To Do
  [f] Weekly Tasks
  Press the character corresponding to your choice, selection will happen immediately. Ctrl+D to cancel
  Moved to Done

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

  $ gtd review -l 'To Do'
  Card 5f679de3b9c40b795bd6e08b
    Name:         Do dishes
    List:         To Do
    Tags:         Household
    Created:      2020-09-20 14:22:27 (1600626147)
    Age:          0:26:33.816457
  gtd.py > description
  # Editor session happened here
  gtd.py > print
  Card 5f679de3b9c40b795bd6e08b
    Name:         Do dishes
    List:         To Do
    Tags:         Household
    Created:      2020-09-20 14:22:27 (1600626147)
    Age:          0:26:51.939956
    Description
      Hello README!
  gtd.py > next
  Card 5f679de74d9e0e69f717686f
    Name:         Write some python
    List:         To Do
    Tags:         Programming
    Created:      2020-09-20 14:22:31 (1600626151)
    Age:          0:26:55.298909
  gtd.py > duedate
  gtd.py > duedate > Oct 01 2020
  Due date set
  gtd.py > print
  Card 5f679de74d9e0e69f717686f
    Name:         Write some python
    List:         To Do
    Tags:         Programming
    Created:      2020-09-20 14:22:31 (1600626151)
    Age:          0:27:16.702654
    Due:          2020-10-01 00:00:00
    Remaining:    10 days, 5:10:12.297117
  gtd.py > quit
  $


Deleting Things
^^^^^^^^^^^^^^^

The ``delete`` subcommand allows you to get rid of lists & cards. By default, cards are archived rather than deleted. You can override this behavior with the ``-f/--force`` flag to ``delete cards``. Lists may not be deleted, so they are archived when you run ``delete list``.

::

  $ gtd add card 'cannon fodder' && gtd delete cards -m cannon
  Successfully added card "cannon fodder"!
  Card 5f67a4df77046c54669bbde0
    Name:         cannon fodder
    List:         Weekly Tasks
    Created:      2020-09-20 14:52:15 (1600627935)
    Age:          0:00:02.914247
  Delete this card? (y/N)
  Card archived!

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
  +----------------+--------------+-----------+---------------+-----+------------+--------------------------+-------------------------------+
  | name           | list         | tags      | desc          | due | activity   | id                       | url                           |
  +----------------+--------------+-----------+---------------+-----+------------+--------------------------+-------------------------------+
  | Clean bathroom | Weekly Tasks | Household |               |     | 2020-09-20 | 5f679de5b92a1708bd7c8c93 | https://trello.com/c/ds3tuegh |
  | Do dishes      | To Do        | Household | Hello README! |     | 2020-09-20 | 5f679de3b9c40b795bd6e08b | https://trello.com/c/8qBVAraN |
  |                |              |           |               |     |            |                          |                               |
  +----------------+--------------+-----------+---------------+-----+------------+--------------------------+-------------------------------+
  $ gtd show cards --by name --fields name,list,tags,desc
  +-------------------------+--------------+-------------+---------------+
  | name                    | list         | tags        | desc          |
  +-------------------------+--------------+-------------+---------------+
  | Clean bathroom          | Weekly Tasks | Household   |               |
  | Do dishes               | To Do        | Household   | Hello README! |
  |                         |              |             |               |
  | Eat a sandwich          | Doing        | Food        |               |
  | Purchase a pomelo       | To Do        | Food        |               |
  | This was written in vim | Done         | Programming |               |
  | Write some python       | To Do        | Programming |               |
  +-------------------------+--------------+-------------+---------------+

You can also filter the fields that are shown with the ``--fields`` argument. By default, ``gtd.py`` will trim down the fields until it fits your current terminal width. It'll only wrap if you have really long card titles relative to the width of your terminal.

The JSON and TSV output formats are handy for programmatically retrieving information from your Trello account. For example, here are two methods to find the shortlink for every card on a list:

::

  $ gtd show cards --by list --fields list,url --tsv | awk '/^Doing/{print $NF}'
  https://trello.com/c/o5Oph6AD
  $ LIST_ID=$(gtd show lists --json | jq -r '.[]|select(.name == "Doing")|.id')
  $ gtd show cards --json | jq ".[]|select(.idList == \"$LIST_ID\")|.shortUrl"
  "https://trello.com/c/o5Oph6AD"

Setup
------

::

  $ pip3 install -U gtd.py
  $ gtd onboard

The ``onboard`` command will assist you through the process of getting a Trello API key for use with this program and putting it in the correct file. This will happen automatically if you run a command that requires authentication without having your API keys set.

If you'd like to enable automatic bash completion for gtd.py, add the following line to your ~/.bashrc:

::

  eval "$(_GTD_COMPLETE=source gtd)"

This relies on ``click``'s internal bash completion engine, so it does not work on other shells like ``sh``, ``csh``, or ``zsh``.

Configuration
--------------

The ``onboard`` command will help you create the configuration file interactively. If you prefer to do the process manually, Trello has a button on their website for temporarily creating an OAUTH key/token. Your API key and secret should be placed in a YAML file with the OAUTH key & token, like this example.

::

  api_key: "your-api-key"
  api_secret: "your-api-secret"
  oauth_token: "your-oauth-token"
  oauth_token_secret: "your-oauth-secret"


All four of these properties are required, ``gtd`` will fail to run without them. There are other optional settings you can define inside your yaml configuration file:

::

  board: "Case-sensitive name of Trello board to use without --board argument"
  inbox_list: "Name of the default list for new cards"
  color: True
  banner: False
  prompt_for_untagged_cards: True
  prompt_for_open_attachments: False


Here are all valid configuration properties with explanations of their behavior:

=============================== ============ ============== =======
Property                        Default      CLI Override   Meaning
=============================== ============ ============== =======
``board``                       Latest board ``-b``         Name of Trello board to use by default
``inbox_list``                  First list                  Name of the list to place new cards
``color``                       True         ``--no-color`` Use ANSI terminal colors?
``banner``                      False        ``--banner``   Print an ASCII art banner on each program run?
``prompt_for_open_attachments`` False                       Ask to open card attachments in ``gtd review``
``prompt_for_untagged_cards``   True                        Ask to tag cards without any tags in ``gtd review``
=============================== ============ ============== =======

This configuration file can be put in a variety of locations within your home folder. The ``onboard`` command will help you with platform detection, putting the configuration file where appropriate given your operating system. When running, ``gtd``` will check all possible locations out of this list:

* ``~/.gtd.yaml``
* ``~/.config/gtd/gtd.yaml``
* ``~/Library/Application Support/gtd/gtd.yaml``
* ``~/.local/etc/gtd.yaml``
* ``~/.local/etc/gtd/gtd.yaml``

Contributing
------------

Contributions would be great! If you think something could be improved just go change it and ask!

There are some tests for the command-line interface to make sure everything works properly. There are currently a few subcommands fully covered with more planned. To run these tests, first use the "onboard" command to create a configuration file. Then add a property ``test_board`` to the configuration file, with the name of a board you can dedicate to running these tests. If the board does not yet exist it will be created during the test run. The tests will destroy an existing board. Then, run:

::

 make test
 # OR,
 python -m pytest tests/

I use ``black`` to format the source code but keep some of my conventions kept in this source since the beginning. I've been using single-quotes for strings and wrapping at 120 character line length, so I use the following command to do the formatting. Please apply it when giving patches.

::

 make black
 # OR,
 black -l 120 -S gtd.py todo/ tests/

Notes
------

* The code is lightly tested. Please (please!) report bugs if you find them.
* This has only been used on Linux and Mac OSX
* Windows is not supported.
* Some naming conventions differ from Trello, most notably "label" is called "tag"

License
--------

BSD. There is a copy included with the software as LICENSE

Copyright 2020 Jamie Luck (delucks)


.. _GTD: https://en.wikipedia.org/wiki/Getting_Things_Done
