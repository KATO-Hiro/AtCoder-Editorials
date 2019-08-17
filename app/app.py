from flask import Flask, render_template, request,url_for, redirect,session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import UserMixin, LoginManager, login_user, logout_user, current_user
from datetime import datetime
from rauth import OAuth1Service
from config import app, db, service, login_manager


class User(UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    description = db.Column(db.String(1024), index=True)
    user_image_url = db.Column(db.String(1024), index=True)
    date_published = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    twitter_id = db.Column(db.String(64), nullable=False, unique=True)


class Editorial(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    contestname = db.Column(db.String(64))
    title = db.Column(db.String(64))
    url = db.Column(db.String(120))
    description = db.Column(db.String(1024))
    like = db.Column(db.Integer)
    user_image_url = db.Column(db.String(1024), index=True)
    user_id=db.Column(db.Integer)

def _normalize_contestname(contestname):
    if isinstance(contestname, str):
        contestname = contestname.strip()
    return contestname


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/search', methods=['GET'])
def contest_search():
    return render_template('search.html')


@app.route('/search/contest/<int:page>', methods=['GET','POST'])
def contest_get(page=1):
    contestname = _normalize_contestname(request.form.get('contestname'))

    per_page = 10
    editorials = Editorial.query.filter_by(contestname=contestname).paginate(page, per_page, error_out=False)

    return render_template('contest.html', contestname=contestname, editorials=editorials)


@app.route('/submited', methods=['POST'])
def submit():
    params = {
        'title': request.form.get('title'),
        'description': request.form.get('description'),
        'contestname': _normalize_contestname(request.form.get('contestname')),
        'url': request.form.get('url'),
        'like':int(0),
        'user_image_url': current_user.user_image_url,
        'username': current_user.username,
        'user_id':current_user.id
    }   

    params['description']=params['description'].replace('\r\n','<br>')
    print(params)

    if (params['description'] is not None or params['url'] is not None) and params['title'] is not None:
        newEditorial = Editorial(**params)
        db.session.add(newEditorial)
        db.session.commit()
        return render_template('submited.html')
    else:
        if params['title'] is None:
            return render_template('error.html', message='Error:タイトルを入力して下さい。')
        else:
            return render_template('error.html', message='Error:URLまたは解説文を入力して下さい。')


@app.route('/user')
def user():
    return render_template('user.html')

@app.route('/ranking')
def ranking():
    return render_template('ranking.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/oauth/twitter')
def oauth_authorize():
    if not current_user.is_anonymous:
        return redirect(url_for('index'))
    else:
        request_token = service.get_request_token(params={
            'oauth_callback': url_for('oauth_callback', provider='twitter', _external=True)
        })
        session['request_token'] = request_token
        return redirect(service.get_authorize_url(request_token[0]))


@app.route('/oauth/twitter/callback')
def oauth_callback():
    request_token = session.pop('request_token')
    oauth_session = service.get_auth_session(
        request_token[0],
        request_token[1],
        data={
            'oauth_verifier': request.args['oauth_verifier']
        }
    )

    profile = oauth_session.get('account/verify_credentials.json').json()

    twitter_id = str(profile.get('id'))
    username = str(profile.get('name'))
    description = str(profile.get('description'))
    profile_image_url = str(profile.get('profile_image_url'))
    user = db.session.query(User).filter(User.twitter_id == twitter_id).first()

    if user:
        user.twitter_id = twitter_id
        user.username = username
    else:
        user = User(
            twitter_id=twitter_id,
            username=username,
            description=description,
            user_image_url=profile_image_url
        )
        db.session.add(user)

    db.session.commit()
    login_user(user, True)
    return redirect(url_for('index'))


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.cli.command('initdb')
def initdb_command():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True)
