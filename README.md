gtd.py
======

The TODO list system for hackers
--------------------------------

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
* Making review interface into a fully fledged cli, with numeric indexes for inspecting elements recently outputted
* Connection retry logic in TrelloConnection
* Make column display mode work with Review mode
* Move banner-display logic to its own function that randomly selects a banner among a group to show (would be entertaining)
* Abstract the trello-specific logic into some kind of an API wrapper class, so we can support other (hopefully floss) systems

I want to improve the review interface. Right now it's inspired by beets, which is a good tool
The idea of having a command prompt to interact with the review interface is interesting to me, because it would
unify the interface: instead of having different prompts and interaction methods for each individual action on a card, you
could use an easily queryable and discoverable system to do it

Another idea; in this repl, use exceptions to control flow through the cards

Review mockup:

```
> add card "some title"
ok
> add card "some title" with description """long string""" with attachments https://jamieluck.com
ok
>
(printed card output)
> help
review: commands
  add
  help
  extract : take url or tag out of title
  tag
  move
  rename
  n/next
  p/print
>
> move to "List name"
Moved to List name
> move to "List name" in "Board Name"
Moved to Board Name/List name
>
> extract url
Found url https://jamieluck.com in title. Should we use this? (Y/n)
? y
Attached https://jamieluck.com
> extract tag
Found tag #"Tag name" in title. Should we use this? (y/N)
? y
Tagged with Tag name
> rename 'Some shit'
Renamed card to Some shit
> next
Card blahblahblah
  Name "Next card"
  ...
>
```

License
-------

BSD. There is a copy included with the software as LICENSE.txt

Copyright 2017 Jamie Luck (delucks)
