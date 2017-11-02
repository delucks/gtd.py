gtd.py
=======

A Fast Command-line Interface for Trello
---------------------------------------

This is a command-line tool that enables you to add, sort, and review cards on Trello rapidly. It is designed to reduce the amount of friction between your thoughts and your TODO list, especially if you never leave the terminal.

The project is named "gtd.py" because it was initially built as a tool for me to maintain a Trello board using the `Getting Things Done<https://en.wikipedia.org/wiki/Getting_Things_Done>`_ task tracking method. I've been actively using this tool for GTD since the first commit; if you're trying to use GTD with Trello this is the tool for you.

Setup
------

::
  pip install gtd.py
  gtd onboard

The ``onboard`` command will assist you through the process of getting a Trello API key for use with this program and putting it in the correct file. Until you've run ``onboard``, all invocations of ``gtd`` will fail.

If you prefer to do the process manually, Trello has a button on their website for temporarily creating an OAUTH key/token. That should be put in a yaml file located at ``$HOME/.config/gtd/gtd.yaml``, formatted like this:

::
  api_key: "your-api-key"
  api_secret: "your-api-secret"
  oauth_token: "your-oauth-token"
  oauth_token_secret: "your-oauth-secret"
  board_name: "The name of the board you want to work with"

The ``board_name`` property will soon not be required.

Notes
------

* The code is not heavily tested beyond my manual use. Please (please!) report bugs if you find them.
* This only works on Unix systems and has only been tested on Linux and Mac OSX
* Some naming conventions differ from Trello, most notably "label" is called "tag"

License
--------

BSD. There is a copy included with the software as LICENSE.txt

Copyright 2017 Jamie Luck (delucks)
