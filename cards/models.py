from cards import app, db


COLOR_MASK = {'white': 0x01, 'blue': 0x02, 'black': 0x04, 'red': 0x08, 'green':
              0x10}

TYPE_MASK = {'artifact': 0x01, 'creature': 0x02, 'land': 0x04, 'instant': 0x08,
             'sorcery': 0x10, 'enchantment': 0x20, 'tribal': 0x40,
             'planeswalker': 0x80}


class User(db.Model):
    id = db.Column(db.String(64), primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(128), index=True)

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

    def __repr__(self):
        return '<User {}>'.format(self.id)


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


# Represents a specific, functionally-identical card.
class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), index=True, unique=True)
    color_byte = db.Column(db.Binary(1))
    type_byte = db.Column(db.Binary(1))
    power = db.Column(db.Integer)
    toughness = db.Column(db.Integer)
    want = db.Column(db.Integer)
    editions = db.relationship('Edition', backref='card', lazy='dynamic',
                               cascade='all, delete-orphan')

    def __repr__(self):
        return '<Card {}>'.format(self.id)

    def have(self):
        return sum(e.have for e in self.editions)

    def need(self):
        return max(self.want - self.have(), 0)

    def extra(self):
        return max(self.have() - self.want, 0)

    def colors(self):
        return {key for key, value in COLOR_MASK.iteritems()
                if (value & self.color_byte)}

    def types(self):
        return {key for key, value in TYPE_MASK.iteritems()
                if (value & self.type_byte)}


# Represents a specific printing of a specific card.
class Edition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    multiverse_id = db.Column(db.Integer, index=True, unique=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'))
    set_id = db.Column(db.Integer, db.ForeignKey('set.id'))
    image_url = db.Column(db.String(128))
    have = db.Column(db.Integer)

    def __repr__(self):
        return '<Edition {}>'.format(self.id)

