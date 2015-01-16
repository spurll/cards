from os import urandom, path


CSRF_ENABLED = True
SECRET_KEY = urandom(30)
PROPAGATE_EXCEPTIONS = True

basedir = path.abspath(path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = "sqlite:///{}".format(path.join(basedir, "app.db"))

LDAP_URI = "ldap://ec2-23-23-226-137.compute-1.amazonaws.com"
LDAP_SEARCH_BASE = "ou=People,dc=invenia,dc=ca"

ADMIN_USERS = ["gem.newman"]

COLORS = ['Colorless', 'White', 'Blue', 'Black', 'Red', 'Green']
TYPES = ['Artifact', 'Creature', 'Enchantment', 'Instant', 'Land',
         'Planeswalker', 'Sorcery', 'Tribal']

DEFAULT_WANT = 4
