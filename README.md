gtd.py
======

The TODO list system for hackers
--------------------------------

This tool is a command-line interface to Trello that allows you to quickly manipulate Kanban cards. It is useful for quickly adding tasks and bits of information to remember for later, and then sorting them appropriately with few keystrokes. It is inspired by the "GTD" methodology, but does not require using it. Since Trello is the only backend for the program (at the moment), you will need a Trello API key to use `gtd.py`.

Setup
-----

I need to work on a quick onboarding flow for this program!! Until then, do this:
Go to [the trello developer page](https://trello.com/app-key) to get your API key for this program. Put it in a yaml file named "gtd.yaml" in the root directory with a layout like "gtd.yaml.example". There are few required keys but all of them are in the example.

Notes
-----

* This only works on Unix systems and has only been tested on Linux
* Some tests require an internet connection
* Naming conventions differ from Trello

For feature requests and the project road map, see the Trello board for this project: https://trello.com/b/LrbDZ6MD/gtdpy

License
-------

BSD. There is a copy included with the software as LICENSE.txt

Copyright 2017 Jamie Luck (delucks)
