import requests

from cards import app, db


COLOR_MASK = {'White': 0x01, 'Blue': 0x02, 'Black': 0x04, 'Red': 0x08,
              'Green': 0x10}

TYPE_MASK = {'Tribal': 0x01, 'Instant': 0x02, 'Sorcery': 0x04,
             'Artifact': 0x08, 'Enchantment': 0x10, 'Land': 0x20,
             'Creature': 0x40, 'Planeswalker': 0x80}


def byte_to_set(mask, b):
    return {key for key, value in mask.iteritems() if (value & b)}


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

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def is_admin(self):
        return self.id in app.config["ADMIN_USERS"]

    def get_id(self):
        return unicode(self.id)


# Represents the various expansions, promotional releases, and collectors sets.
class Set(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(3), index=True)
    name = db.Column(db.String(128), index=True, unique=True)
    alternate_name = db.Column(db.String(128), unique=True)
    release_date = db.Column(db.Date)
    cards = db.relationship('Edition', backref='set', lazy='dynamic',
                            cascade='all, delete-orphan')

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
    power = db.Column(db.SmallInteger)
    toughness = db.Column(db.SmallInteger)
    want = db.Column(db.Integer, default=0)
    important = db.Column(db.Boolean, default=False)
    uncertain = db.Column(db.Boolean, default=False)
    editions = db.relationship('Edition', backref='card', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return '<Card {}>'.format(self.id)

    def __str__(self):
        return '<Card {}>'.format(self.name)

    def have(self):
        return sum(e.have for e in self.editions)

    def need(self):
        return max(self.want - self.have(), 0)

    def extra(self):
        return max(self.have() - self.want, 0)

    def colors(self):
        return byte_to_set(COLOR_MASK, self.color_byte)

    def types(self):
        return byte_to_set(TYPE_MASK, self.type_byte)

    def color(self):
        colors = self.colors()
        if len(colors) == 0:
            return 'Colorless'
        elif len(colors) > 1:
            return 'Mulitcolored'
        else:
            return colors.pop()

    def type(self):
        return " ".join(self.types())

    def editions_by_release(self):
        return self.editions.join(Set).order_by(Set.release_date.desc())


# Represents a specific printing of a specific card.
class Edition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    multiverse_id = db.Column(db.Integer, index=True, unique=True)
    collector_number = db.Column(db.Integer, index=True)
    rarity = db.Column(db.String(1))
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'))
    set_id = db.Column(db.Integer, db.ForeignKey('set.id'))
    have = db.Column(db.Integer, default=0)

    def __repr__(self):
        return '<Edition {}>'.format(self.id)

    def __str__(self):
        return '<Edition {} ({})>'.format(self.card.name, self.set.name)

    def image_url(self):
        return ('https://image.deckbrew.com/mtg/multiverseid/{}.jpg'
                .format(self.multiverse_id))

    def deckbrew_url(self):
        return ('https://api.deckbrew.com/mtg/cards?multiverseid={}'
                .format(self.multiverse_id))

    def price(self):
        p = None
        r = requests.get(self.deckbrew_url())
        j = r.json()

        if j and (r.status_code == requests.codes.ok):
            e = [e for e in j[0].get('editions')
                 if e.get('multiverse_id') == self.multiverse_id]
            if e:
                p = e[0].get('price', dict()).get('median')
                if p:
                    p = float(p) / 100.0

        return p

