# Written by Gem Newman. This work is licensed under a Creative Commons         
# Attribution-NonCommercial-ShareAlike 3.0 Unported License.                    


from flask import render_template, flash, redirect, session, url_for, request, g
from flask.ext.login import login_user, logout_user, current_user, login_required
from wtforms import BooleanField
from wtforms.fields.html5 import IntegerField
from wtforms.validators import NumberRange
from urllib import urlencode
import ldap

from cards import db, app, api, lm
from forms import LoginForm, BrowseForm, DetailsForm, AddForm
from models import User, Set, Card, Edition
from authenticate import authenticate


@app.route('/')
@app.route('/index')
def index():
    return redirect(url_for('browse'))


@app.route('/browse', methods=['GET', 'POST'])
@login_required
def browse():
    """
    Browse collection alphabetically, or by set or release date.
    """
    user = g.user   # NOT USED.

    form = BrowseForm()

    filters = {'color': form.color.data.split('|') if form.color.data else [],
               'type': form.type.data.split('|') if form.type.data else [],
               'set': form.set.data.split('|') if form.set.data else [],
               'collection': form.collection.data.split('|')
                             if form.collection.data else []}

    # Consider sending (and receiving) page numbers to keep queries shorter.

    cards = api.browse(filters=filters, group='set', web=True)
    headers, submenu = build_submenu(filters)

    title = 'Browse Collection'
    return render_template('browse.html', title=title, user=user, form=form,
                           headers=headers, submenu=submenu, cards=cards)


@app.route('/search')
@login_required
def search():
    """
    Search collection for a specific card.
    """
    user = g.user   # NOT USED.


    # CODE HERE

    # Bottom part of the page is just the browse page, but with a search bar at
    # the top.


    title = "Search Collection"
    return render_template("search.html", title=title, user=user)


@app.route('/details', methods=['GET', 'POST'])
@login_required
def details():
    """
    View card details.
    """
    user = g.user   # NOT USED.

    name = request.args.get('card')
    if not name:
        flash('No card specified.')
        return redirect(url_for('index'))

    card = api.details(name=name, web=True)

    if not card:
        flash('No details for {} found in the database.'.format(name))
        return redirect(url_for('index'))

    # We need to duplicate the "have" field for each printing of the card. This
    # necessitates making a new class every time.
    class CurrentDetailsForm(DetailsForm):
        want = IntegerField("Want", default=card['want'],
                            validators=[NumberRange(min=0)])
        important = BooleanField("Important", default=card['important'])
        uncertain = BooleanField("Uncertain", default=card['uncertain'])

    for edition in card['editions']:
        field = IntegerField(id=edition['set'], default=edition['have'],
                             validators=[NumberRange(min=0)], label='Have')
        setattr(CurrentDetailsForm, edition['set'], field)

    form = CurrentDetailsForm()
    title = card['name']
    return render_template("details.html", title=title, user=user, form=form,
                           card=card)


@app.route('/add/card', methods=['GET', 'POST'])
@login_required
def add_card():
    """
    Add a card to the database (or if it exists in the DB, simply update the
    number that you have/want). If you add a card that already exists, it will
    still set the want number and fetch and update all printings.
    """
    user = g.user

    cards = []

    # First, you enter a card name (and numeric field for how many you want).
    form = AddForm()
    if form.is_submitted():
        if form.validate_on_submit():
            # Look for the specified card.
            cards = api.find_card(form.name.data)

            if not cards:
                # No cards were found. Warn, and have the user try again.
                flash('No cards found matching "{}".'.format(form.data.name))

            else:
                # Success! Exactly one card was found! Add it, then redirect.
                try:
                    api.add_card(cards[0], want=form.want.data)
                    return redirect(url_for('details', card=cards[0]))

                except Exception as e:
                    flash('Error adding card: {}'.format(e))

        else:
            flash('Error: ' + form.errors)
            print('Unable to validate. Error: ' + form.errors)

    # If you're here, either you haven't specified a card to add yet, or you're
    # selecting a card from among a list of possible matches.
    title = "Add Card"
    return render_template("add.html", title=title, user=user, form=form,
                           cards=cards)


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
    return render_template("set.html", title=title, user=user)


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


def build_submenu(filters):
    """
    Defines what sub-menu items will be displayed in the "Browse" submenu.
    """

    headers = [
        'Card Name', 'Color', 'Type', 'Cost', 'H', 'W', 'N'
    ]

    submenu =  [
        {
            'title': 'Collection',
            'items': [
                {'label': label, 'active': label in filters['collection']}
                for label in ['Owned', 'Wanted']
            ]
        },
        {
            'title': 'Color',
            'items': [
                {'label': label, 'active': label in filters['color']}
                for label in app.config['COLORS']
            ]
        },
        {
            'title': 'Type',
            'items': [
                {'label': label, 'active': label in filters['type']}
                for label in app.config['TYPES']
            ]
        },
        {
            'title': 'Set',
            'items': [
                {'label': label, 'active': label in filters['set']}
                for label in [s.name for s in
                    Set.query.order_by(Set.release_date.desc(), Set.name)]]
        },
    ]

    return headers, submenu

