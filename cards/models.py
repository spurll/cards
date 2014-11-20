from cards import app, db


COLOR_MASK = {'White': 0x01, 'Blue': 0x02, 'Black': 0x04, 'Red': 0x08, 'Green':
              0x10}

TYPE_MASK = {'Artifact': 0x01, 'Creature': 0x02, 'Land': 0x04, 'Instant': 0x08,
             'Sorcery': 0x10, 'Enchantment': 0x20, 'Tribal': 0x40,
             'Planeswalker': 0x80}


def byte_to_set(mask, b):
    return {key for key, value in mask.iteritems() if (value & b)}


def set_to_byte(mask, s):
    return reduce(lambda x, y: x | mask[y], s, 0x00)


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
    color_byte = db.Column(db.Binary(1))
    type_byte = db.Column(db.Binary(1))
    power = db.Column(db.Integer)
    toughness = db.Column(db.Integer)
    editions = db.relationship('Edition', backref='card', lazy='dynamic',
                               cascade='all, delete-orphan')
    want = db.relationship('Want', backref='card', uselist=False,
                           cascade='all, delete-orphan')

    def __repr__(self):
        return '<Card {}>'.format(self.id)

    def __str__(self):
        return '<Card {}>'.format(self.name)

    def have(self):
        return sum(e.have() for e in self.editions)

    def want(self):
        return self.want.number

    def need(self):
        return max(self.want() - self.have(), 0)

    def extra(self):
        return max(self.have() - self.want(), 0)

    def colors(self):
        return byte_to_set(COLOR_MASK, self.color_byte)

    def types(self):
        return byte_to_set(TYPE_MASK, self.type_byte)


# Represents a specific printing of a specific card.
class Edition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    multiverse_id = db.Column(db.Integer, index=True, unique=True)
    rarity = db.Column(db.String(1))
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'))
    set_id = db.Column(db.Integer, db.ForeignKey('set.id'))
    collection = db.relationship('Collection', backref = 'edition',
                                 uselist=False, cascade='all, delete-orphan')

    def __repr__(self):
        return '<Edition {}>'.format(self.id)

    def __str__(self):
        return '<Edition {} ({})>'.format(self.card.name, self.set.name)

    def image_url(self):
        return ('https://image.deckbrew.com/mtg/multiverseid/{}.jpg'
                .format(self.multiverse_id))

    def have(self):
        return self.have.number


# Represent what specific cards you have.
class Collection(db.Model):
    edition_id = db.Column(db.Integer, db.ForeignKey('edition.id'),
                           primary_key=True)
    number = db.Column(db.Integer)

    def __repr__(self):
        return '<Collection {}>'.format(self.id)


# Represents what cards you're looking for.
class Want(db.Model):
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), primary_key=True)
    number = db.Column(db.Integer)
    important = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<Want {}>'.format(self.id)
