from functools import reduce
from flask import url_for
from bs4 import BeautifulSoup
import dryscrape, re

from cards import app, db


COLOR_MASK = {'White': 0x01, 'Blue': 0x02, 'Black': 0x04, 'Red': 0x08,
              'Green': 0x10}

# Should have 'Conspiracy' in here, but I don't want to add another byte...
TYPE_MASK = {'Tribal': 0x01, 'Instant': 0x02, 'Sorcery': 0x04,
             'Artifact': 0x08, 'Enchantment': 0x10, 'Land': 0x20,
             'Creature': 0x40, 'Planeswalker': 0x80}

ALTERNATE_NAMES = {
    'Limited Edition Alpha': 'Alpha',
    'Limited Edition Beta': 'Beta',
    'Unlimited Edition': 'Unlimited',
    'Revised Edition': 'Revised',
    'Classic Sixth Edition': 'Sixth Edition',
    'Magic 2014 Core Set': 'Magic 2014',
    'Magic 2015 Core Set': 'Magic 2015',
    'Ravnica: City of Guilds': 'Ravnica',
    'Deckmasters: Garfield vs. Finkel': 'Deckmasters',
    'Modern Masters (2015 Edition)': 'Modern Masters 2015',
    'Planechase 2012 Edition': 'Planechase 2012',
    'Commander 2013 Edition': 'Commander 2013',
    'Commander 2014': 'Commander 2014 Edition',     # Okay, this is dumb.
    'Commander 2015': 'Commander 2015 Edition',
}

MCI_CODES = {
    'Friday Night Magic': 'fnmp',
    'Wizards Play Network': 'grc',
    'Judge Gift Program': 'jr',
    'Magic Player Rewards': 'mprp',
    'Grand Prix': 'gpx',
    'Magic Game Day': 'mgdc',
    'Prerelease Events': 'ptc',
    'Launch Parties': 'mlp',
    'Media Inserts': 'mbp',
    'Champs and States': 'cp'
}


def byte_to_set(mask, b):
    return {key for key, value in mask.items() if (value & b)}


def set_to_byte(mask, s):
    return reduce(lambda x, y: x | mask.get(y, 0x00), s, 0x00)


class User(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True)

    def __repr__(self):
        return '<User {}>'.format(self.id)

    def __str__(self):
        return '<User {}>'.format(self.name)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def is_admin(self):
        return self.id in app.config["ADMIN_USERS"]

    def get_id(self):
        return self.id


# Represents the various expansions, promotional releases, and collectors sets.
class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(4), index=True)
    name = db.Column(db.String, index=True, unique=True)
    release_date = db.Column(db.Date)
    cards = db.relationship('Edition', backref='set', lazy='dynamic',
                            cascade='all, delete-orphan')

    def __repr__(self):
        return '<Set {}>'.format(self.code)

    def __str__(self):
        return '<Set {}>'.format(self.name)

    @property
    def alternate_name(self):
        return ALTERNATE_NAMES.get(self.name)

    @property
    def mci_code(self):
        return MCI_CODES.get(self.name, self.code.lower())

    def __repr__(self):
        return '<Set {}>'.format(self.id)

    def __str__(self):
        return '<Set {}>'.format(self.name)


# Represents a specific, functionally-identical card.
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), index=True, unique=True)
    color_byte = db.Column(db.SmallInteger)
    type_byte = db.Column(db.SmallInteger)
    cost = db.Column(db.String(20))
    power = db.Column(db.String(3))
    toughness = db.Column(db.String(3))
    want = db.Column(db.Integer, default=0)
    important = db.Column(db.Boolean, default=False)
    uncertain = db.Column(db.Boolean, default=False)
    editions = db.relationship('Edition', backref='card', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return '<Card {}>'.format(self.name)

    def __str__(self):
        return '<Card {}>'.format(self.name)

    @property
    def have(self):
        return sum(e.have for e in self.editions)

    @property
    def need(self):
        return max(self.want - self.have, 0)

    @property
    def extra(self):
        return max(self.have - self.want, 0)

    @property
    def colors(self):
        return byte_to_set(COLOR_MASK, self.color_byte)

    @property
    def types(self):
        return byte_to_set(TYPE_MASK, self.type_byte)

    @property
    def pt(self):
        return self.power + '/' + self.toughness if self.power else ''

    @property
    def color(self):
        colors = self.colors
        if len(colors) == 0:
            return 'Colorless'
        elif len(colors) > 1:
            return 'Mulitcolored'
        else:
            return colors.pop()

    @property
    def type(self):
        return " ".join(self.types)

    @property
    def editions_by_release(self):
        return self.editions.join(Set).order_by(Set.release_date.desc())

    @property
    def web_name(self):
        return '<a href="{}">{}</a>'.format(
            url_for('details', card=self.name), self.name
        )

    @property
    def web_cost(self):
        if self.cost:
            mana_tags = [
                '<img src="{}">'.format(
                    url_for('static', filename='{}{}.png'.format(
                        m.group(1), m.group(2)
                    ))
                )
                for m in re.finditer(r'{([^/]?)/?([^/]?)}', self.cost)
            ]
            return '<div class="mana">{}</div>'.format("".join(mana_tags))
        else:
            return ''

    def details(self, web=False):
        return {
            'name': self.name,
            'color': self.color,
            'type': self.type,
            'cost': self.web_cost if web else self.cost,
            'power': self.power,
            'toughness': self.toughness,
            'want': self.want,
            'have': self.have,
            'need': self.need,
            'important': self.important,
            'uncertain': self.uncertain,
            'editions': [
                {
                    'set': edition.set.name,
                    'have': edition.have,
                    'collector_number': edition.collector_number,
                    'rarity': edition.rarity,
                    'price': edition.price,
                    'image_url': edition.image_url
                }
                for edition in self.editions_by_release.all()
            ]
        }


# Represents a specific printing of a specific card.
class Edition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    multiverse_id = db.Column(db.Integer, index=True)
    collector_number = db.Column(db.String(4), index=True)  # Supports DFCs.
    rarity = db.Column(db.String(1))
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'))
    set_id = db.Column(db.Integer, db.ForeignKey('set.id'))
    have = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Edition {} ({})>'.format(self.card.name, self.set.code)

    def __str__(self):
        return '<Edition {} ({})>'.format(self.card.name, self.set.code)

    @property
    def image_url(self):
        return ('https://image.deckbrew.com/mtg/multiverseid/{}.jpg'
                .format(self.multiverse_id))

    @property
    def deckbrew_url(self):
        return ('https://api.deckbrew.com/mtg/cards?multiverseid={}'
                .format(self.multiverse_id))

    @property
    def mci_url(self):
        return ('http://magiccards.info/{}/en/{}.html'
                .format(self.set.mci_code, self.collector_number))

    @property
    def price(self):
        price = None

        # Unfortunately we need JavaScript support.
        session = dryscrape.Session()
        session.visit(self.mci_url)
        response = session.body()

        if response:
            soup = BeautifulSoup(response, 'html.parser')
            price_tag = soup.find('td', class_='TCGPPriceMid')

            if price_tag and price_tag.a:
                price = price_tag.a.string

        return price

    def dict(self):
        return {
            'set': self.set.name,
            'have': self.have,
            'price': self.price,
            'image_url': self.image_url
        }

    def tuple(self, web=False):
        return (
            self.card.web_name if web else self.card.name,
            self.card.color,
            self.card.type,
            self.card.web_cost if web else self.card.cost,
            self.have,
            self.card.want,
            self.card.need
        )
