 # -*- coding: utf-8 -*-
import bottle
import datetime
from bottle import *
from google.appengine.api import users
from google.appengine.ext import ndb
  
app = Bottle()

database_key = ndb.Key('Application', 'submitted_apps')

class Participant(ndb.Model):
    participant_fn = ndb.StringProperty(required=True)
    participand_nickname = ndb.StringProperty(required=True)
    participant_age = ndb.IntegerProperty(required=True)

class Application(ndb.Model):
    author = ndb.UserProperty(required=True)
    author_fn = ndb.StringProperty(required=True)
    author_phone = ndb.StringProperty(required=True)
    author_bdate = ndb.DateProperty(required=True)
    author_mail = ndb.StringProperty(required=True)
    author_contacts = ndb.StringProperty(required=True)
    content = ndb.TextProperty(indexed=False)
    participants = ndb.StructuredProperty(Participant, repeated=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    app_type = ndb.StringProperty(required=True, choices=set([u"Сценка", u"Групповое дефиле", u"Караоке", u"Дефиле", u"Другое" ]))

@app.route('/')
def main_page():
    message = ""
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    else:
        users.create_logout_url(request.url)

    application_query = Application.query(ancestor=database_key).order(-Application.date) 
    applications = application_query.fetch(10)
    
    output = template('main.html', content = applications)
    return output

@app.route('/sign', method='POST')
def write_form():
    
		
    application = Application(parent=database_key)
    application.content = request.forms.get('content')
    application.author_fn = request.forms.get('author_fn')
    application.author_phone = request.forms.get('author_phone')
    application.author_bdate = datetime.strptime(request.forms.get('author_bdate'), '%d-%m-%Y')
    application.author_mail = request.forms.get('author_mail')
    application.app_type = request.forms.get('app_type').decode('utf-8')
    application.author = users.get_current_user()
    
    
    if not application.author:
        redirect(users.create_login_url(request.url))
	

    application.put()

	
	
    redirect(request.url)


@app.error(403)
def Error403(code):
    return 'Get your codes right dude, you caused some error!'

@app.error(404)
def Error404(code):
    return 'Stop cowboy, what are you trying to find?'

run(app=app, server='gae', debug=True)