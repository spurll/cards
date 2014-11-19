Card Collector
==============

A web program (with a Flask and SQLite back-end) that keeps track of a Magic: The Gathering collection

Usage
=====

Requirements
------------

* flask
* flask-login
* flask-wtf
* flask-sqlalchemy
* sqlalchemy
* python-ldap

Configuration
-------------

Before starting the server for the first time, run `db_create.py`.

Starting the Server
-------------------

Start the server with `run.py`. By default it will be accessible at `localhost:9999`. To make the server world-accessible or for other options, see `run.py -h`.

Bugs and Feature Requests
=========================

Feature Requests
----------------

The following features may be implemented in the future:

* When adding a card, the set should be a drop-down list in order of release date (with sets with no date at the bottom)
* Ability to add cards that are not yet listed in DeckBrew or on MagicCards.info (spoiler cards)
 * Should probably be implemented by first adding the set, and then associating the card with it in some way outisde of DeckBrew
 * Ability to edit the name of those cards, as sometimes they're inaccurate
* Various viewing options:
 * View sets (with columns as in a spreadsheet) chronologically
 * View cards by set
 * Toggle to ignore cards you have "enough" of
 * Field to ignore cards you have at least X of
* Search by card name
* Ability to view card details (including what editions there are, oracle text, image, etc.) via lookup of the card on DeckBrew with its multiverse ID (if it has one)
* Batch import of information from a CSV file
* Ability to add "alternate names" for sets (e.g., "Ravnica" for "Ravnica: City of Guilds", "Magic 2015" for "Magic 2015 Core Set", "Commander 2014" for "Commander 2014 Edition", "Sixth Edition" for "Classic Sixth Edition", etc.)
* Lists and searches can page through multiple results
* Ability to update card info, which will search DeckBrew for information to update it (called automatically when you view details if some of the details are missing?)

Known Bugs
----------

None

DeckBrew API
============

This project makes use of the [DeckBrew API](http://deckbrew.com/api/).

License Information
===================

Written by Gem Newman. [GitHub](https://github.com/spurll/) | [Blog](http://www.startleddisbelief.com) | [Twitter](https://twitter.com/spurll)

This work is licensed under Creative Commons [BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).
