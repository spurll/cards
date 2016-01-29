from datetime import datetime, date
from dateutil.parser import parse
import re, requests


BASE_REQUEST = 'https://api.deckbrew.com/mtg/cards'


def find_card(name):
    """
    Searches DeckBrew for cards that match the specified name. If there is an
    exact match among the cards (e.g., the search was for "Shock", which
    returns a bunch of results as well as that specific card) return ONLY the
    exact match. If there's no exact match, return all of them.
    """
    cards = []

    name = name.lower().replace('aether', '\xe6ther')

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
                    print('Unable to find a Multiverse ID for "{}". This '
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
                d = parse(match[-1], default=date(1993, 1, 1))
            except:
                print("Warning: Can't fetch release date for {}. Unknown "
                      'format "{}".'.format(set_name, match[-1]))
        else:
            print('Warning: No release date found for {}.'.format(set_name))
    else:
        print("Warning: Can't fetch release date for {}. Unable to connect to"
              "{}.".format(set_name, request))

    return d
