gtd.py
======

This is a commandline tool that enables rapid interaction with a kanban-type task organization system. It enables, but does not require, the task tracking methodolgy called "getting things done", thus the name. It uses Trello as the backend for the program, you will require an API key in order to use this program.

Setup
-----

Go to [the trello developer page](https://trello.com/app-key) to get your API key for this program. Put it in a yaml file named "gtd.yaml" in the root directory with a layout like "gtd.yaml.example".

Modes
-----

* add: Create a new card, tag, or list
* grep: Search through all cards on the board
* show: Output cards to standard output
* batch: Tag, move, or delete cards in very few keystrokes
* review: Present a rich interface to modify cards
* workflow: Print out the process description

Notes
-----

* This only works on Unix systems and has only been tested on Linux
* Some tests require an internet connection
* Naming conventions differ from Trello's because I intend on eventually abstracting the todo list provider out of the way

TODO
----

* Add an audit trail of logging or metrics emission so you can see where things are going
* Translate #tag into adding that tag, then removing that part of the title
* Method to set the due date of the "weekly"/"Monthly" lists all at once
* Argument that can select multiple list names to filter
* Abstraction layer for the todo list provider so this can be used with sites other than Trello
* Tests
