jard Collector
==============

A Python 3/Flask web program that keeps track of a Magic: The Gathering collection.

Usage
=====

Requirements
------------

* flask
* flask-login
* flask-wtf
* flask-sqlalchemy
* sqlalchemy
* ldap3
* beautifulsoup4
* python-dateutil

Configuration
-------------

You'll need to create a `config.py` file, which specifies details such as which LDAP server to use. A sample configuration file can be found at `sample_config.py`.

Starting the Server
-------------------

Start the server with `run.py`. By default it will be accessible at `localhost:9999`. To make the server world-accessible or for other options, see `run.py -h`.

Bugs and Feature Requests
=========================

Feature Requests
----------------

Short-term goals:

* Add colourless mana symbol to static dir (probably {C})
* Add cards
* Increment function (takes card, set, and number default: 1); can decrement if passed -1
* Ability to filter by rarity, certainty, and priority too
* Ability to increment (or decrement) number of a card printing from the browse view
* Batch import of information from a CSV file
* Search by card name
* Ability to update card info, which will search DeckBrew for information to update it
* Test for split cards, DFCs, and level up creatures (power/toughness, price, type, etc.)

Long-term goals (features that may be implemented in the future):

* "Add Set" searches the set and adds all cards with `add_card` (can be set to add only uncommons+, rares+, etc.; by default doesn't add basic land)
* Ability to delete a card (wholesale) from the DB (takes all editions with it)
* Ability to add cards that are not yet listed in DeckBrew or on MagicCards.info (spoiler cards)
 * Should probably be implemented by first adding the set, and then associating the card with it in some way outside of DeckBrew
 * Ability to edit the name of those cards, as sometimes they're inaccurate
* Ability to add "alternate names" for sets (e.g., "Ravnica" for "Ravnica: City of Guilds", "Magic 2015" for "Magic 2015 Core Set", "Commander 2014" for "Commander 2014 Edition", "Sixth Edition" for "Classic Sixth Edition", etc.)
* Use pages of results for browsing/searching (you'll need to also return how many pages of results there are)
* Mouse-over popups of the card image

Known Bugs
----------

* There's still a problem in the HTML that causes the page to be slightly too tall (so it scrolls a little even when it shouldn't)
* TCGPlayer killed DeckBrew integration, so prices are all gone. Should still be able to scrape pages from the DeckBrew `store_url` field (such as http://shop.tcgplayer.com/magic/mirrodin/lightning-greaves)
* Currently all users share the same collection (might not be worth fixing)
* It's possible that very common, short names won't return results when `api.find_card` is called (because DeckBrew will only return the first 100 items, and the one we're looking for might not be in the list)

DeckBrew API
============

This project makes use of the [DeckBrew API](http://deckbrew.com/api/).

License Information
===================

Written by Gem Newman. [Website](http://spurll.com) | [GitHub](https://github.com/spurll/) | [Twitter](https://twitter.com/spurll)

This work is licensed under Creative Commons [BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/).

Remember: [GitHub is not my CV.](https://blog.jcoglan.com/2013/11/15/why-github-is-not-your-cv/)
