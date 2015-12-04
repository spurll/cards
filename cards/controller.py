from collections import OrderedDict
import re, csv

from cards import db, deckbrew
from cards.models import (
    User, Set, Card, Edition, set_to_byte, COLOR_MASK, TYPE_MASK
)


RARITY = {
    'common': 'C',
    'uncommon': 'U',
    'rare': 'R',
    'mythic': 'M',
    'basic': 'L',
    'special': 'S'
}

CSV_COLUMNS = [
    'important',
    'release_date',
    'set',
    'name',
    'price',
    'want',
    'have',
    'need',
    'uncertain'
]


"""
Returns all cards matching the filters provided. If the optional group argument
is specified, an OrderedDict grouping the results by the specified value will
be returned instead of a list.

filters: dict containing what column to filter and a list of valid values
group: string to group results by "set", "color", or "type" (default None)
sort: list of attributes to sort by (default release date and collector #)
"""
def fetch(filters=None, group=None, sort=None, page_size=None, page_number=1):
    if filters is None:
        filters = {}

    if sort is None:
        sort = [Set.release_date.desc(), Edition.collector_number, Card.name]

    # Define query and filters.
    query = Edition.query.join(Card).join(Set)
    where = []

    if filters.get('color'):
        if isinstance(filters['color'], str):
            filters['color'] = [filters['color']]

        # Only return cards with at least one of the colors listed.
        c = Card.color_byte.op('&')(set_to_byte(COLOR_MASK, filters['color']))

        # Special case to deal with colorless cards (they have no matches).
        if 'Colorless' in filters['color']:
            c = c | (Card.color_byte == 0x00)

        where.append(c)

    if filters.get('type'):
        if isinstance(filters['type'], str):
            filters['type'] = [filters['type']]

        # Only return cards with at least one of the types listed.
        c = Card.type_byte.op('&')(set_to_byte(TYPE_MASK, filters['type']))
        where.append(c)

    if filters.get('set'):
        if isinstance(filters['set'], str):
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
            group = lambda x: x.card.color
        elif group == "type":
            group = lambda x: x.card.type
        else:
            print('Invalid grouping criterion "{}". Grouping by set instead.'
                  .format(group))
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


"""
Adds a card to the database.
"""
def add_card(name, want=None, have=dict(), important=None, uncertain=None):
    card = deckbrew.find_card(name)

    if not card:
        raise Exception('No cards found with the name "{}".'.format(name))
    if len(card) > 1:
        raise Exception('{} possible cards found with names matching "{}".'
                        .format(len(card), name))

    card = card[0]

    # Colors and card types are stored returned by DeckBrew in lowercase. They
    # need to be capitalized for dictionary mapping lookups.
    card['colors'] = map(lambda x: x.capitalize(), card.get('colors', []))
    card['types'] = map(lambda x: x.capitalize(), card.get('types', []))

    # Identify all printings of the card.
    editions = set()
    for edition in card.get('editions', []):
        # Some set names are remarkably dumb and/or contain non-ASCII chars.
        # At least one From the Vault is listed in DeckBrew with a date, too.
        edition['set'] = re.sub(r'Magic: The Gathering[^A-Za-z]*', '',
                                edition.get('set'))
        edition['set'] = re.sub(r'(From the Vault:( \w+)+?) \(\d{4}\)', r'\1',
                                edition.get('set'))

        # Some sets have multiple "editions" of the same card (Arabian Nights
        # had two printings that were essentially identical, while some older
        # sets like Fallen Empires and Alliances had alternate art for the
        # commons, some Judge Foils were printed twice, etc.). This could be
        # dealt with mandating a unique constraint on multiverse_id in a given
        # set (instead of name), but it's easiest to just roll all of those
        # editions into one. For my purposes, it's not worth the trouble.
        if edition['set'] in [e.set.name for e in editions]:
            print(
                'Skipping additional printings of {} from {}.'
                .format(card['name'], edition['set'])
            )
            continue

        # First, find and/or build the necessary Set objects.
        if not (edition.get('set') and edition.get('set_id')):
            print(
                'Warning: Set information for this edition is incomplete: '
                '{} ({})'.format(edition.get('set'), edition.get('set_id'))
            )
            continue

        s = Set.query.filter(Set.name == edition['set']).scalar()

        if not s:
            # Build the necessary Set object.
            print('Adding set {}.'.format(edition['set']))
            s = Set(
                code=edition['set_id'],
                name=edition['set'],
                release_date=deckbrew.release_date(edition['set'])
            )

        # Second, find and/or build the necessary Edition objects.
        e = Edition.query.join(Set).join(Card).filter(
            (Set.name == edition['set']) & (Card.name == card['name'])
        ).scalar()

        in_collection = have.pop(edition['set'], None)
        if e:
            # Update fields in the Edition object if necessary.
            if (in_collection is not None) and (e.have != in_collection):
                print(
                    'Updating number of {} ({}) in collection from {} to {}.'
                    .format(
                        card['name'], edition['set'], e.have, in_collection
                    )
                )
                e.have = in_collection

        else:
            # Build the necessary Edition object.
            print('Adding edition of {} from {}.'
                  .format(card['name'], edition['set']))
            e = Edition(
                multiverse_id=edition.get('multiverse_id'),
                collector_number=edition.get('number'),
                rarity=rarity(edition.get('rarity')),
                have=in_collection if in_collection else 0,
                set=s   # Associate the Set object with this Edition.
            )

        editions.add(e)

    # Finally, find and/or build the Card object.
    c = Card.query.filter(Card.name == card['name']).scalar()

    if c:
        # Update fields in the Card object if necessary.
        if (want is not None) and (c.want != want):
            print('Updating number of {} wanted from {} to {}.'
                  .format(card['name'], c.want, want))
            c.want = want

        if (important is not None) and (c.important != important):
            print('Marking {} as {}important.'
                  .format(card['name'], 'not ' if not important else ''))
            c.important = important

        if (uncertain is not None) and (c.uncertain != uncertain):
            print('Setting number of {} in collection to {}certain.'
                  .format(card['name'], 'un' if uncertain else ''))
            c.uncertain = uncertain

        # Attach the Edition objects to the Card object.
        c.editions = editions
        # If we previously had editions that don't exist in DeckBrew now...?
        # TODO: What does the above comment mean?

    else:
        # Build the necessary Card object.
        print('Adding card {}.'.format(card['name']))

        c = Card(
            name=card['name'],
            color_byte=set_to_byte(COLOR_MASK, set(card.get('colors', []))),
            type_byte=set_to_byte(TYPE_MASK, set(card.get('types', []))),
            cost=card.get('cost'),
            power=card.get('power'),
            toughness=card.get('toughness'),
            want=want,
            important=bool(important),   # None and False are distinct only if
            uncertain=bool(uncertain),   # the card already exists.
            editions=editions
        )

    # Warn if some of the sets where you have copies don't actually have
    # editions on record.
    if have.keys():
        # TODO: Fix this, because DeckBrew isn't always up-to-date with all
        # printings of a card, and some sets just don't seem to appear in
        # DeckBrew at all, like SDCC promos and World Championship decks.
        print(
            'Warning: The following editions weee not added to the DB because '
            'the printings could not be found on DeckBrew: {}'.format(have)
        )

    # Add and commit to DB.
    try:
        db.session.add(c)
        db.session.commit()
    except Exception as e:
        print('Error: Unable to issue database commit: {}\nRolling back...'
              .format(e))
        db.session.rollback()
        raise e


"""
Takes a file name (or open file?) and imports it using multiple calls to the
add_card function.
"""
def import_csv(file_name):
    with open(file_name, 'r') as csv_file:
        reader = csv.reader(csv_file)

        # Skip the header.
        next(reader, None)

        # Convert each row from a list to a dictionary for easier indexing.
        rows = [
            {column: r[index] for index, column in enumerate(CSV_COLUMNS)}
            for r in reader
        ]

    cards = {r['name'] for r in rows}

    for card in cards:
        want = sum([int(r['want']) for r in rows if r['name'] == card])
        have = {r['set']: int(r['have']) for r in rows if r['name'] == card}
        important = any([r['important'] for r in rows if r['name'] == card])
        uncertain = any([r['uncertain'] for r in rows if r['name'] == card])

        print('Importing {} {} {} {} {}'
              .format(card, want, have, important, uncertain))
        add_card(card, want, have, important, uncertain)


def export_csv(f):
    """
    Exports the entire DB to a CSV file for easy backup.
    """

    # Should assign "want" values such that they fit with the editions and all
    # add up to the total want value. (Probably just assign it to the latest
    # printing, then set all others to zero? Or something more complicated.)


    # Test importing an exported file. Should be no errors!

    # TODO: Write this.

    pass


def rarity(word):
    """
    Converts the rarity words used by DeckBrew into single-character codes.
    """

    if not word:
        print('Warning: No rarity provided.')

    r = RARITY.get(word)

    if not r:
        r = word[0].upper()
        print('Unknown rarity "{}". Best guess is "{}".'.format(word, r))

    return r
