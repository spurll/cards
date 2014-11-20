# Written by Gem Newman. This work is licensed under a Creative Commons         
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.                    


from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
import ldap

from cards import app, db, lm
from forms import LoginForm, AddForm
from models import User, Set, Card, Edition
from authenticate import authenticate


COLORS = {'White', 'Blue', 'Black', 'Red', 'Green'}
TYPES = {'Artifact', 'Creature', 'Enchantment', 'Instant', 'Land',
         'Planeswalker', 'Sorcery', 'Tribal'}


@app.route('/')
@app.route('/index')
def index():
    return redirect(url_for('browse'))


@app.route('/browse', methods=['GET'])
@login_required
def browse():
    """
    Browse collection alphabetically, or by set or release date.
    """
    user = g.user
    sets = [s.name for s in Set.query.all()]
    filters = {'color': request.args.get('color', COLORS),
               'type': request.args.get('type', TYPES),
               'set': request.args.get('set', sets)}


    # CODE HERE



    # BY DEFAULT, BROWSE SHOULD ONLY DISPLAY CARDS YOU HAVE OR WANT


    # FILTERS NOT USED YET.
#    cards = [Edition.query.filter(Edition.

#    cards = [Card.query.filter(!Card.colors().isdisjoint(filters['color']) &
#                               !Card.types().isdisjoint(filters['type']) &
#                               !Card.sets
    sets = [s.name for s in Set.query.order_by(Set.release_date.desc())]

    # Dummy Data
    sets = ["Unlimited", "Beta", "Alpha"]
    cards = { 'Unlimited': [ ['Mox Jet', 'Colorless', 'Artifact', '0', '', 1, 0, 1], ['Mox Sapphire', 'Colorless', 'Artifact', '0', '', 1, 1, 0], ], 'Beta': [ ['Mox Jet', 'Colorless', 'Artifact', '0', '', 1, 0, 1], ['Mox Sapphire', 'Colorless', 'Artifact', '0', '', 1, 1, 0], ], 'Alpha': [ ['Mox Jet', 'Colorless', 'Artifact', '0', '', 1, 0, 1], ['Mox Sapphire', 'Colorless', 'Artifact', '0', '', 1, 1, 0], ] }
    # Dummy Data

    sections = sets
    headers = ['Name', 'Color', 'Type', 'Cost', 'P/T', 'Have', 'Need', 'Want']

    print [i for cat in filters.values() for i in cat]
    title = 'Browse Collection'
    return render_template('browse.html', title=title, user=user,
                           colors=COLORS, types=TYPES, sets=sets,
                           sections=sections, headers=headers, cards=cards,
                           filters=[i for cat in filters.values() for i in cat])


@app.route('/search')
@login_required
def search():
    """
    Search collection for a specific card.
    """
    user = g.user


    # CODE HERE


    title = "Search Collection"
    return render_template("search.html", title=title, user=user)


@app.route('/details')
@login_required
def details():
    """
    View card details.
    """
    user = g.user


    # CODE HERE


    title = card.name
    return render_template("details.html", title=title, user=user)


@app.route('/add/card')
@login_required
def add_card():
    """
    Add a card to the database (or if it exists in the DB, simply update the
    number that you have/want).
    """
    user = g.user


    # CODE HERE

    # When you add a card, it should have a numeric field for how many you
    # want, and numeric fields for EACH PRINTING indicating how many you have
    # (defaulting to zero for each, and sorted by set release date).


    title = card.name
    return render_template("add_card.html", title=title, user=user)


@app.route('/add/set')
@login_required
def add_set():
    """
    Adds a set/edition to the database. Should only be needed for sets that
    are recently announced (and that have no printings yet). Spoiler stuff.
    """
    user = g.user


    # CODE HERE

    # We'll need some way to update information after printings and additional
    # details are available.

    title = card.name
    return render_template("add_set.html", title=title, user=user)


@app.route('/update/database')
@login_required
def update_db():
    """
    Pulls all cards that exist in DeckBrew into the local database.
    """
    user = g.user


    # CODE HERE

    # Probably needs some sort of asynchronous call...? This is definitely
    # going to time out. But how do we make sure that other stuff won't
    # interfere with the update?


    title = "Update Database"
    return render_template("update_db.html", title=title, user=user)


@app.route('/import')
@login_required
def import_csv():
    """
    Imports an existing collection from a CSV file.
    """
    user = g.user


    # CODE HERE


    title = "Import Collection from CSV"
    return render_template("import.html", title=title, user=user)


@app.route('/export')
@login_required
def export_csv():
    """
    Exports the card DB collection to a CSV file. (Only exports cards with
    "haves" or "wants".)
    """
    user = g.user


    # CODE HERE


    title = "Export Collection to CSV"
    return render_template("export.html", title=title, user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Logs the user in using LDAP authentication.
    """
    if g.user is not None and g.user.is_authenticated():
        return redirect(url_for('index'))

    form = LoginForm()

    if request.method == 'GET':
        return render_template('login.html', title="Log In", form=form)

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        try:
            print "Logging in..."
            user = authenticate(username, password)
        except ldap.INVALID_CREDENTIALS:
            user = None

        if not user:
            print "Login failed."
            flash("Login failed.")
            return render_template('login.html', title="Log In", form=form)

        if user and user.is_authenticated():
            db_user = User.query.get(user.id)
            if db_user is None:
                db.session.add(user)
                db.session.commit()

            login_user(user, remember=form.remember.data)

            return redirect(request.args.get('next') or url_for('index'))

    return render_template('login.html', title="Log In", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@lm.user_loader
def load_user(id):
    return User.query.get(id)


@app.before_request
def before_request():
    g.user = current_user

