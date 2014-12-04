from flask import url_for
from collections import OrderedDict
import re

from cards import db
from models import User, Set, Card, Edition, set_to_byte, COLOR_MASK, TYPE_MASK


def fetch(filters={}, group=None, sort=None, page_size=None, page_number=1):
    """
    Returns all cards matching the filters provided. If the optional group
    argument is specified, an OrderedDict grouping the results by the specified
    value will be returned instead of a list.

    filters: dict containing what column to filter and a list of valid values
    group: string to group results by "set", "color", or "type" (default None)
    sort: list of attributes to sort by (default release date and collector #)
    """

    if not sort:
        sort = [Set.release_date.desc(), Edition.collector_number, Card.name]

    # Define query and filters.
    query = Edition.query.join(Card).join(Set)
    where = []

    if filters.get('color'):
        if isinstance(filters['color'], basestring):
            filters['color'] = [filters['color']]

        # Only return cards with at least one of the colors listed.
        c = Card.color_byte.op('&')(set_to_byte(COLOR_MASK, filters['color']))

        # Special case to deal with colorless cards (they have no matches).
        if 'Colorless' in filters['color']:
            c = c | (Card.color_byte == 0x00)

        where.append(c)

    if filters.get('type'):
        if isinstance(filters['type'], basestring):
            filters['type'] = [filters['type']]

        # Only return cards with at least one of the types listed.
        c = Card.type_byte.op('&')(set_to_byte(TYPE_MASK, filters['type']))
        where.append(c)

    if filters.get('set'):
        if isinstance(filters['set'], basestring):
            filters['set'] = [filters['set']]

        # Only return editions of cards printed in the sets listed.
        where.append(Set.name.in_(filters['set']))

    if 'Owned' in filters.get('collection', []):
        # Only return editions where you have at least one copy of the card.
        where.append(Edition.have >= 1)

    # Apply filters and ordering to query.
    query = query.filter(*where).order_by(*sort)

    # Apply pagination functions.
    if page_size:
        query = query.limit(page_size).offset(page_size * (page_number - 1))

    # Execute query.
    result = query.all()

    # Finish filtering by cards you need (difficult to do in the query itself).
    if 'Wanted' in filters.get('collection', []):
        # Only return cards where you need at least one of the cards.
        result = filter(lambda e: e.card.need() >= 1, result)

    # Group.
    if group:
        cards = OrderedDict()

        # Define grouping method.
        if group == "set":
            group = lambda x: x.set.name
        elif group == "color":
            group = lambda x: x.card.color()
        elif group == "type":
            group = lambda x: x.card.type()
        else:
            print ('Invalid grouping criterion "{}". Grouping by set '
                   'instead.'.format(group))
            group = lambda x: x.set.name

        for card in result:
            group_name = group(card)
            if group_name in cards:
                cards[group_name].append(card)
            else:
                cards[group_name] = [card]

    else:
        cards = result

    return cards


def browse(filters={}, group=None, sort=None, page_size=None, page_number=1,
           web=False):
    """
    Like fetch, only it returns tuples instead of Edition objects.
    """

    cards = fetch(filters, group, sort, page_size, page_number)

    if not group:
        cards = [edition_to_tuple(c, web) for c in cards]
    else:
        for key, value in cards.iteritems():
            cards[key] = [edition_to_tuple(c, web) for c in value]

    return cards


def details(name, web=False):
    """
    Takes a card name and returns the details in a dict. Some data comes from
    the DB, but more is fetched from the internet.
    """

    card = Card.query.filter(Card.name == name).first()

    if card:
        card = {
            'name': card.name,
            'color': card.color(),
            'type': card.type(),
            'cost': mana_symbol_tags(card.cost) if web else card.cost,
            'power': card.power,
            'toughness': card.toughness,
            'want': card.want,
            'have': card.have(),
            'need': card.need(),
            'important': card.important,
            'uncertain': card.uncertain,
            'editions': [
                {
                    'set': edition.set.name,
                    'have': edition.have,
                    'collector_number': edition.collector_number,
                    'rarity': edition.rarity,
                    'price': edition.price(),
                    'image_url': edition.image_url()
                }
                for edition in card.editions_by_release().all()
            ]
        }

    return card


def edition_to_dict(edition, web=False):
    """
    Returns a dictionary for the details view.
    """

    name = link_card_name(edition.card.name) if web else edition.card.name
    cost = mana_symbol_tags(edition.card.cost) if web else edition.card.cost

    return {'set': edition.set.name,
            'have': edition.have,
            'image_url': edition.image_url()}


def edition_to_tuple(edition, web=False):
    """
    Returns a row for the browse view.
    """

    name = link_card_name(edition.card.name) if web else edition.card.name
    cost = mana_symbol_tags(edition.card.cost) if web else edition.card.cost
    pt = ('{}/{}'.format(edition.card.power, edition.card.toughness)
          if edition.card.power else '')

    # Does not include set.
    return (name, edition.card.color(), edition.card.type(), cost, pt,
            edition.have, edition.card.want, edition.card.need())


def link_card_name(name):
    return '<a href="{}">{}</a>'.format(url_for('details', card=name), name)


def mana_symbol_tags(cost):
    """
    Converts a string containing mana symbol information into a series of HTML
    <img> tags representing that cost.
    """

    if cost:
        pattern = r'{([^/]?)/?([^/]?)}'
        replacement =  r'<img src="/static/\1\2.png">'
        mana_tag = re.sub(pattern, replacement, cost)
        return '<div class="mana">{}</div>'.format(mana_tag)
    else:
        return ''

