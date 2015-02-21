# -*- coding: utf-8 -*-
import bottle
import datetime
from bottle import *
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore

  
app = Bottle()

database_key = ndb.Key('Application', 'submitted_apps')
comments_key = ndb.Key('Comments', 'comments')
app_types = [u"Сценка", u"Групповое дефиле", u"Караоке", u"Дефиле", u"Другое" ]
counter_id = 1
statuses={"sent":"Отправлена", "hold": "Ожидает ответа", "wait": "В рассмотрении", "deny": "Отклонена", "accept": "Принята"}

class Counter(ndb.Model):
    counter = ndb.IntegerProperty(default=1)

class Participant(ndb.Model):
    participant_fn = ndb.StringProperty(required=True)
    participant_nickname = ndb.StringProperty(required=True)
    participant_age = ndb.IntegerProperty(required=True)
    
class Comments(ndb.Model):
    comment_date = ndb.DateTimeProperty(auto_now_add=True)
    comment = ndb.TextProperty(indexed=False)
    author = ndb.UserProperty(required=True)
    application = ndb.StringProperty(required=True)
   
class Application(ndb.Model):
    author = ndb.UserProperty(required=True)
    author_fn = ndb.StringProperty(required=True)
    author_phone = ndb.StringProperty(required=True)
    author_bdate = ndb.DateProperty(required=True)
    author_mail = ndb.StringProperty(required=True)
    author_contacts = ndb.StringProperty(required=False)
    content = ndb.TextProperty(indexed=False)
    participants = ndb.StructuredProperty(Participant, repeated=True)
    date = ndb.DateTimeProperty(auto_now_add=True)
    app_type = ndb.StringProperty(required=True, choices=set(app_types))
    app_title = ndb.StringProperty(required=False)
    app_origin = ndb.StringProperty(required=True)
    app_status = ndb.StringProperty(required=True)
    city = ndb.StringProperty(required=True)
    number = ndb.IntegerProperty(required=True)  
    test_blob = ndb.StringProperty(required=False)
    
    
@app.route('/')
def main_page():
    
    
    message = ""
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    else:
        users.create_logout_url(request.url)

    application_query = Application.query(Application.author == user).order(+Application.number) 
    applications = application_query.fetch()
    
    output = template('main.html', apps = applications, app_types=app_types, statuses=statuses, upload_url = blobstore.create_upload_url('/upload'))
    
    return output

    
@app.route('/add')    
def app_add():
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    else:
        users.create_logout_url(request.url)
   
    output = template('app-edit.html', app_types=app_types, action="add", statuses=statuses)
    response.charset = 'UTF-8'
    return output

@ndb.transactional    
@app.route('/add', method='POST')
def new_app():
		
    application = Application(parent=database_key)
    application.content = request.forms.get('content')
    application.author_fn = request.forms.get('author_fn')
    application.author_phone = request.forms.get('author_phone')
    application.author_bdate = datetime.strptime(request.forms.get('author_bdate'), '%d-%m-%Y')
    application.author_mail = request.forms.get('author_mail')
    application.author_contacts = request.forms.get('author_contacts')
    application.app_type = request.forms.get('app_type').decode('utf-8')
    application.app_title = request.forms.get('app_title')
    application.app_origin = request.forms.get('app_origin')
    application.city = request.forms.get('city')
    application.app_status = "sent"
    application.author = users.get_current_user()
    
    data = request.files.data
    
    
        
    participants_list = []
    
    for i in range(10):
      fullname = request.forms.get("participant_fn_%d" % i)
      nickname = request.forms.get("participant_nickname_%d" % i)
      age = request.forms.get("participant_age_%d" % i)
      #participants_list.append([fullname, nickname, age, "participant_fn_%d" % i])
      if fullname and nickname and age:
        try:
          participants_list.append(Participant(participant_fn=fullname, 
                                               participant_nickname=nickname,
                                               participant_age=int(age) )
                                   )
        except:
          redirect("/error")
    #print participants_list
    application.participants = participants_list 
    
    if not application.author:
        redirect(users.create_login_url(request.url))

    counter = Counter.get_by_id(counter_id)
    if counter is None:
        counter = Counter(id=counter_id)
    counter.counter += 1
    
    application.number = counter.counter
    
    counter.put()    
    application.put()
    response.charset = 'UTF-8'
    #return "%s" % participants_list  
    redirect("/")


#not going to work, just adding stuff
@app.route('/edit/<url_id>')
def edit_post(url_id):
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))

    apps = ndb.Key(urlsafe=url_id)
    application = Application.query(ancestor=apps).fetch()
    
    if (application[0].author != user) and (not users.is_current_user_admin()):
        redirect('/')          
    
    try:
      comments = Comments.query(Comments.application == url_id).order(+Comments.comment_date).fetch()
    except:
      comments = ""
    
    upload_url = blobstore.create_upload_url('/edit')
    
    output = template('app-edit.html', app = application[0], action="edit", comments=comments, url_id=url_id, upload_url=upload_url, app_types=app_types, statuses=statuses )
    

    return output
    #return "success"
    
    
#not going to work, just adding stuff
@app.route('/edit', method='POST')
def edit_post():
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    
        
    
    
    
    
    url_id = request.forms.get('url_id')
    #return url_id
    application = ndb.Key(urlsafe=url_id).get()

    if application.author != user and not users.is_current_user_admin() :
        redirect('/')  
   
    application.content = request.forms.get('content')
    application.author_fn = request.forms.get('author_fn')
    application.author_phone = request.forms.get('author_phone')  
    #application.author_bdate = datetime.strptime(request.forms.get('author_bdate'), '%d-%m-%Y')
    #application.author_mail = request.forms.get('author_mail')
    #application.author_contacts = request.forms.get('author_contacts')
    application.app_type = request.forms.get('app_type').decode('utf-8')
    application.app_title = request.forms.get('app_title')
    application.app_origin = request.forms.get('app_origin')
    #application.city = request.forms.get('city')
    #application.app_status = "sent"
    
    upload = request.files.get('upload')
    #blob_info = upload
    #file_headers =[]
    #for i in header:
    #    file_headers.append(i)
    #return file_headers
    #application.test_blob = header
    
    
    
    participants_list = []
    
    for i in range(10):
      fullname = request.forms.get("participant_fn_%d" % i)
      nickname = request.forms.get("participant_nickname_%d" % i)
      age = request.forms.get("participant_age_%d" % i)
      delete = request.forms.get("participant_delete_%d" % i)
      #participants_list.append([fullname, nickname, age, "participant_fn_%d" % i])
      if fullname and nickname and age and not delete:
        try:
          participants_list.append(Participant(participant_fn=fullname, 
                                               participant_nickname=nickname,
                                               participant_age=int(age) )
                                   )
        except:
          redirect("/error")
    #print participants_list
    application.participants = participants_list 
           
    comment = Comments(parent=comments_key)
    comment_body = request.forms.get('comment')
    if comment_body:
        comment.comment = request.forms.get('comment')
        comment.author = user
        comment.application = url_id
        comment.put()       
    application.put()
    
    

    return "success"
    #return application
    #redirect('/')  


@app.route('/error')
def error_page():  
  return "Error!"

@app.error(403)
def Error403(code):
    return 'Get your codes right dude, you caused some error!'

@app.error(404)
def Error404(code):
    return 'Stop cowboy, what are you trying to find?'

run(app=app, server='gae', debug=True)