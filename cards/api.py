from flask import url_for
from collections import OrderedDict
from datetime import datetime, date
from dateutil import parser
import re, requests, csv

from cards import db
from models import User, Set, Card, Edition, set_to_byte, COLOR_MASK, TYPE_MASK


BASE_REQUEST = 'https://api.deckbrew.com/mtg/cards'

RARITY = {
    'common': 'C',
    'uncommon': 'U',
    'rare': 'R',
    'mythic': 'M',
    'basic': 'L',
    'special': 'S'
}

ALTERNATE_NAMES = {
    'Limited Edition Alpha': 'Alpha',
    'Limited Edition Beta': 'Beta',
    'Unlimited Edition': 'Unlimited',
    'Revised Edition': 'Revised',
    'Classic Sixth Edition': 'Sixth Edition',
    'Magic 2014 Core Set': 'Magic 2014',
    'Magic 2015 Core Set': 'Magic 2015',
    'Magic 2016 Core Set': 'Magic 2016',            # Making a guess, here...
    'Ravnica: City of Guilds': 'Ravnica',
    'Deckmasters: Garfield vs. Finkel': 'Deckmasters',
    'Modern Masters (2015 Edition)': 'Modern Masters 2015',
    'Planechase 2012 Edition': 'Planechase 2012',
    'Commander 2013 Edition': 'Commander 2013',
    'Commander 2014': 'Commander 2014 Edition',     # Okay, this is dumb.
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

    # Query.first() returns the first one (or None).
    # Query.scalar() returns one (or None); if there are more, it errors.
    # Query.one() returns one; if there are more or fewer, it errors.
    card = Card.query.filter(Card.name == name).scalar()

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


def find_card(name):
    """
    Searches DeckBrew for cards that match the specified name. If there is an
    exact match among the cards (e.g., the search was for "Shock", which
    returns a bunch of results as well as that specific card) return ONLY the
    exact match. If there's no exact match, return all of them.
    """
    cards = []

    name = unicode(name.lower(), 'utf8').replace('aether', u'\xe6ther')

    # To handle split cards, look up one side, get the multiverse ID, look up
    # all cards with that multiverse ID (which is for a specific printing), and
    # construct a name with the two "sides" of the card that show up (first the
    # "a" side then the "b" side). This is basically the equivalent of
    # searching "Ice // Partridge" and getting "Fire // Ice", but whatever.

    # Check for split card syntax ("Fire // Ice") and remove it.
    split = [i.strip() for i in name.split('//')]
    if len(split) > 1:
        name = split[0]

    request = BASE_REQUEST + '?name=' + name
    r = requests.get(request)
    cards = r.json()

    if cards and (r.status_code == requests.codes.ok):
        # Grab split status and Multiverse ID to resolve split card confusion.
        split = [any([e.get('layout') == 'split'
                     for e in c.get('editions', [])])
                 for c in cards]
        m_ids = [[e.get('multiverse_id') for e in c.get('editions', [])
                  if e.get('multiverse_id')]
                 for c in cards]

        names = [c['name'].lower() for c in cards]
        if (len(cards) > 1) and (name.lower() in names):
            index = names.index(name.lower())
            cards = [cards[index]]
            split = [split[index]]
            m_ids = [m_ids[index]]

        # If there are split cards, we've only found one side of them. Find the
        # other, then combine the cards and join the names together in the
        # proper order.
        for i in range(len(cards)):
            if split[i]:
                if not m_ids[i]:
                    print ('Unable to find a Multiverse ID for "{}". This '
                           'usually occurs when a card exists only as a promo.'
                           ' Sorry!').format(cards[i])
                    continue

                request = BASE_REQUEST + '?m={}'.format(m_ids[i][0])
                r = requests.get(request)
                card_pair = r.json()

                if len(card_pair) == 2 and (r.status_code==requests.codes.ok):
                    # Might be listed in the wrong order.
                    reverse = 'b' in card_pair[0]['editions'][0].get('number')

                    # Determine the split card's name.
                    new_name = [c.get('name') for c in card_pair]
                    if reverse: new_name.reverse()
                    cards[i]['name'] = ' // '.join(new_name)

                    # Determine the split card's card types.
                    cards[i]['types'] = list(set(card_pair[0].get('types', [])
                                             + card_pair[1].get('types', [])))

                    # Determine the split card's colours.
                    cards[i]['colors'] = list(set(card_pair[0].get('colors',[])
                                             + card_pair[1].get('colors', [])))

                    # Determine the split card's cost.
                    new_cost = [c.get('cost') for c in card_pair]
                    if reverse: new_cost.reverse()
                    cards[i]['cost'] = ' // '.join(new_cost)

                    # Determine the split card's text. (Not used, but meh.)
                    new_text = [c.get('text') for c in card_pair]
                    if reverse: new_text.reverse()
                    cards[i]['text'] = '\n//\n'.join(new_text)

    return cards


def find_card_name(name):
    """
    Searches DeckBrew for cards matching the specified name and returns the
    matching name(s) only.
    """
    return [c.get('name') for c in find_card(name)]


def add_card(name, want=None, have=dict(), important=None, uncertain=None):
    """
    Adds a card to the database.
    """
    card = find_card(name)

    if not card:
        raise Exception(u'No cards found with the name "{}".'.format(name))
    if len(card) > 1:
        raise Exception(u'{} possible cards found with names matching "{}".'
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
            print (u'Skipping additional printings of {} from {}.'
                   .format(card['name'], edition['set']))
            continue

        # First, find and/or build the necessary Set objects.
        if not (edition.get('set') and edition.get('set_id')):
            print (u'Warning: Set information for this edition is incomplete: '
                   '{} ({})'.format(edition.get('set'), edition.get('set_id')))
            continue

        s = Set.query.filter(Set.name == edition['set']).scalar()

        if not s:
            # Build the necessary Set object.
            print u'Adding set {}.'.format(edition['set'])
            s = Set(
                code=edition['set_id'],
                name=edition['set'],
                alternate_name=alternate_name(edition['set']),
                release_date=release_date(edition['set'])
            )

        # Second, find and/or build the necessary Edition objects.
        e = Edition.query.join(Set).join(Card).filter(
            (Set.name == edition['set']) & (Card.name == card['name'])
        ).scalar()

        in_collection = have.pop(edition['set'], None)
        if e:
            # Update fields in the Edition object if necessary.
            if (in_collection is not None) and (e.have != in_collection):
                print (u'Updating number of {} ({}) in collection from {} to '
                       u'{}.'.format(card['name'], edition['set'], e.have,
                       in_collection))
                e.have = in_collection

        else:
            # Build the necessary Edition object.
            print u'Adding edition of {} from {}.'.format(card['name'],
                                                         edition['set'])
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
            print (u'Updating number of {} wanted from {} to {}.'
                   .format(card['name'], c.want, want))
            c.want = want

        if (important is not None) and (c.important != important):
            print (u'Marking {} as {}important.'
                   .format(card['name'], 'not ' if not important else ''))
            c.important = important

        if (uncertain is not None) and (c.uncertain != uncertain):
            print (u'Setting number of {} in collection to {}certain.'
                   .format(card['name'], 'un' if uncertain else ''))
            c.uncertain = uncertain

        # Attach the Edition objects to the Card object.
        c.editions = editions
        # If we previously had editions that don't exist in DeckBrew now...?

    else:
        # Build the necessary Card object.
        print u'Adding card {}.'.format(card['name'])

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
        print ('Warning: The following editions were not added to the DB '
               'because the printings could not be found on DeckBrew: {}'
               .format(have))

    # Add and commit to DB.
    try:
        db.session.add(c)
        db.session.commit()
    except Exception as e:
        print ('Error: Unable to issue database commit: {}\nRolling back...'
               .format(e))
        db.session.rollback()
        raise e


def import_csv(file_name):
    """
    Takes a file name (or open file?) and imports it using multiple calls to
    the add_card function.
    """

    with open(file_name, 'rb') as csv_file:
        reader = csv.reader(csv_file)

        # Skip the header.
        next(reader, None)

        # Convert each row from a list to a dictionary for easier indexing.
        rows = [{column: r[index] for index, column in enumerate(CSV_COLUMNS)}
                for r in reader]

    cards = {r['name'] for r in rows}

    for card in cards:
        want = sum([int(r['want']) for r in rows if r['name'] == card])
        have = {r['set']: int(r['have']) for r in rows if r['name'] == card}
        important = any([r['important'] for r in rows if r['name'] == card])
        uncertain = any([r['uncertain'] for r in rows if r['name'] == card])

        print ('Importing {} {} {} {} {}'
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


    pass



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
          if edition.card.power is not '' else '')

    # Does not include set.
    return (name, edition.card.color(), edition.card.type(), cost,
            edition.have, edition.card.want, edition.card.need())


def link_card_name(name):
    return u'<a href="{}">{}</a>'.format(url_for('details', card=name), name)


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


def alternate_name(set_name):
    """
    Looks up the alternate name for a set from a dictionary. Pretty useless.
    """

    if not set_name:
        print 'Warning: No set name provided.'

    return ALTERNATE_NAMES.get(set_name)


def rarity(word):
    """
    Converts the rarity words used by DeckBrew into single-character codes.
    """

    if not word:
        print 'Warning: No rarity provided.'

    r = RARITY.get(word)

    if not r:
        r = word[0].upper()
        print 'Unknown rarity "{}". Best guess is "{}".'.format(word, r)

    return r


def release_date(set_name):
    """
    Searches a Wikipedia article using regular expressions (I know, I know...)
    to determine the release date of a given set.
    """

    set_name = set_name.replace(' "Timeshifted"', '')
    d = None

    request = 'http://en.wikipedia.org/wiki/List_of_Magic:_The_Gathering_sets'
    r = requests.get(request)
    html = r.text

    if html and (r.status_code == requests.codes.ok):
        pattern = r'<td><i.*?>' + set_name + r'<.*?\/i>.*?<\/td>\n?(<td>.*?\n?.*?<\/td>\n?){2,4}<td>(.*? [0-9]{4})<'
        match = re.search(pattern, html)

        if match:
            match = match.groups()
            try:
                d = parser.parse(match[-1], default=date(1993, 1, 1))
            except:
                print ("Warning: Can't fetch release date for {}. Unknown "
                       'format "{}".'.format(set_name, match[-1]))
        else:
            print 'Warning: No release date found for {}.'.format(set_name)
    else:
        print ("Warning: Can't fetch release date for {}. Unable to connect to"
               "{}.".format(set_name, request))

    return d

