
import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        db = get_db()
        error = None
        
        if not username:
            error = 'Username is required.'
        elif not email: 
            error = 'Email is required'
        elif not password:
            error = 'Password is required.'
        elif not confirm_password: 
            error = 'Please confirm your password'
        elif password != confirm_password: 
            error = 'Your passwords didnt match'
        elif db.execute(
            'SELECT id FROM user WHERE username = ?', (username,)
        ).fetchone() is not None:
            error = 'User {} is already registered.'.format(username)

        if error is None:
            db.execute(
                'INSERT INTO user (username, password, email) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), email)
            )
            db.commit()
            return redirect(url_for('auth.login'))

        flash(error)

    return render_template('auth/register.html')

@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')
        

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))



def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

@bp.route('/account')
@login_required
def account(): 
    return render_template('auth/account.html')

@bp.route('/settings')
@login_required
def settings(): 
    return render_template('auth/settings.html')




@bp.route('/change_password', methods=('GET', 'POST'))
@login_required
def change_password(): 
    if request.method == 'POST':
        password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
        error = None
        db = get_db()
        username = g.user['username']
        

        if not password: 
            error = 'Please enter your password'
        elif not new_password: 
            error = 'Please enter your new password'
        elif not confirm_new_password: 
            error = 'Please confirm your new password'
        elif new_password != confirm_new_password: 
            error = "Your new passwords don't match"
        elif new_password == password: 
            error = 'Your new password is the same as your old password'
        if error is None:
            db.execute(
                'UPDATE user SET password = "{}" WHERE username = "{}"'.format(generate_password_hash(new_password), username)
            )
            db.commit()
            return redirect(url_for('auth.account'))
        flash(error)
    return render_template('auth/change_password.html')

@bp.route('/change_email', methods=('GET', 'POST'))
@login_required
def change_email(): 
    if request.method == 'POST': 
        email = request.form['current_email']
        new_email = request.form['new_email']
        db = get_db() 
        error = None; 
        username = g.user['username']

        if not email: 
            error = 'please enter your email'
        
        elif not new_email: 
            error = 'please enter your new email'
        
        elif new_email == email: 
            error = 'your new email must be different than your original email'

        if error is None:
            db.execute(
                'UPDATE user SET email = "{}" WHERE username = "{}"'.format(new_email, username)
            )
            db.commit()
            return redirect(url_for('auth.account'))
        flash(error)


    return render_template('auth/change_email.html')

        
