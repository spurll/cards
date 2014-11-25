from collections import OrderedDict

from cards import db
from models import User, Set, Card, Edition, set_to_byte, COLOR_MASK, TYPE_MASK


def fetch(filters={}, group=None, sort=None):
    """
    Returns all cards matching the filters provided. If the optional group
    argument is specified, an OrderedDict grouping the results by the specified
    value will be returned instead of a list.

    filters: dict containing what column to filter and a list of valid values
    group: string to group results by "set", "color", or "type" (default None)
    sort: list of attributes to sort by (default release date and collector #)
    """

    if not sort:
        sort = [Set.release_date.desc(), Edition.collector_number]

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

    if filters.get('have'):
        # Only return editions where you have at least the number listed.
        where.append(Edition.have >= filters['have'])

    # Query.
    result = query.filter(*where).order_by(*sort).all()

    # Finish filtering by cards you need (difficult to do in the query itself).
    if filters.get('need'):
        # Only return cards where you need at least the number listed.
        result = filter(lambda e: e.card.need() >= filters['need'], result)

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


def browse(filters={}, group=None, sort=None):
    """
    Like fetch, only it returns dicts instead of Edition objects.
    """

    cards = fetch(filters, group, sort)

    if not group:
        cards = [to_tuple(c) for c in cards]
    else:
        for key, value in cards.iteritems():
            cards[key] = [to_tuple(c) for c in value]

    return cards


def to_dict(edition):
    return {'name': edition.card.name,
            'set': edition.set.name,
            'color': edition.card.color(),
            'type': edition.card.type(),
            'cost': edition.card.cost,
            'power': edition.card.power,
            'toughness': edition.card.toughness,
            'have': edition.have,
            'want': edition.card.want,
            'need': edition.card.need()}


def to_tuple(edition):
    # Does not include set.
    return (edition.card.name,
            edition.card.color(),
            edition.card.type(),
            edition.card.cost,
            '{}/{}'.format(edition.card.power, edition.card.toughness)
                if edition.card.power else '',
            edition.have,
            edition.card.want,
            edition.card.need())

