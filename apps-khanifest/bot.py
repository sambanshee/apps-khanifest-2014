# -*- coding: utf-8 -*-
import bottle
import base64
import datetime
import webob
from bottle import *
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.ext import blobstore
from multipart import parse_options_header
from google.appengine.ext.blobstore import BlobInfo, BlobKey
import re

def decode_field(field):
    try:
        return base64.b64decode(str(field).decode('utf-8'))
    except:
        #return field.decode('utf-8')
        return field


  
app = Bottle()

database_key = ndb.Key('Application', 'submitted_apps')
comments_key = ndb.Key('Comments', 'comments')
app_types = {"play":"Сценка", "group":"Групповое дефиле", "karaoke":"Караоке", "defile":"Дефиле", "other":"Другое" }
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
    app_type = ndb.StringProperty(required=True)
    app_title = ndb.StringProperty(required=False)
    app_origin = ndb.StringProperty(required=True)
    app_status = ndb.StringProperty(required=True)
    city = ndb.StringProperty(required=True)
    number = ndb.IntegerProperty(required=True)  
    test_blob = ndb.StringProperty(repeated=True)
    rehersals = ndb.StringProperty(repeated=True, indexed=False, required=False)
    timing = ndb.StringProperty(required=True, indexed=False)  
    
    
@app.route('/')
def main_page():
    
    
    message = ""
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    else:
        users.create_logout_url(request.url)
    
    if users.is_current_user_admin:
        application_query = Application.query().order(+Application.number) 
    else:
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
   
    output = template('app-edit.html', app_types=app_types, action="add", statuses=statuses,)
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
    #application.app_type = request.forms.get('app_type').decode('utf-8')
    application.app_type = request.forms.get('app_type')
    application.app_title = request.forms.get('app_title')
    application.app_origin = request.forms.get('app_origin')
    application.city = request.forms.get('city')
    application.timing = request.forms.get('timing')
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

    #return "%s" % participants_list  
    redirect("/")


@app.route('/view/<url_id>')    
def view_application(url_id):
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))

    application = ndb.Key(urlsafe=url_id).get()
    if (application.author != user) and (not users.is_current_user_admin()):
        redirect('/')              

    try:
      comments = Comments.query(Comments.application == url_id).order(+Comments.comment_date).fetch()
    except:
      comments = ""        
    
    upload_url = blobstore.create_upload_url('/fileadd')
    
    output = template('app-list.html', app = application, action="view", comments=comments, upload_url=upload_url, url_id=url_id, app_types=app_types, statuses=statuses )
    
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return output

@app.route('/fileadd', method='POST')    
def file_add():    
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'    
    url_id = request.forms.get('url_id')
    application = ndb.Key(urlsafe=url_id).get()
    if application.author != user and not users.is_current_user_admin() :
        redirect('/')
    try:
        upload = request.files["upload"]
        blob_data = parse_options_header(upload.content_type)[1]
        blob_key =  blob_data["blob-key"]
        if application.test_blob:
            application.test_blob.append(blob_key)
        else:
            application.test_blob = [blob_key]
        application.put()
    except:
        pass
    redirect('/view/%s' % url_id)
       
@app.route('/ytadd', method='POST')
def youtube_add():
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'    
    url_id = request.forms.get('url_id')
    application = ndb.Key(urlsafe=url_id).get()
    if application.author != user and not users.is_current_user_admin() :
        redirect('/')
        
    try:
        rehersal = request.forms.get('rehersal')
    except:
        rehersal = None    
        
    if rehersal:
        match = re.search(r"(?:youtube\.com\/\S*(?:(?:\/e(?:mbed))?\/|watch\?(?:\S*?&?v\=))|youtu\.be\/)([a-zA-Z0-9_-]{6,11})", rehersal)
        if match:
            rehersal = match.group(1)
            
    if application.rehersals and rehersal:
        application.rehersals.append(rehersal)
        application.put()
    elif rehersal and not application.rehersals:
        application.rehersals = [rehersal]
        application.put()
        
    redirect('/view/%s' % url_id)

@app.route('/commentadd', method='POST')    
def comment_add():
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    response.headers['Content-Type'] = 'text/html; charset=utf-8'    
    url_id = request.forms.get('url_id')
    application = ndb.Key(urlsafe=url_id).get()
    if application.author != user and not users.is_current_user_admin() :
        redirect('/')

    comment = Comments(parent=comments_key)
    comment_body = request.forms.get('comment')
    if comment_body:
        comment.comment = comment_body
        comment.author = user
        comment.application = url_id
        comment.put()       
        
    redirect('/view/%s' % url_id)

        
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
    
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    return output
    #return "success"
    
    
'''
upload parsed thanks to http://stackoverflow.com/questions/13021255/using-bottle-py-and-blobstore-gae
'''

@app.route('/edit', method='POST')
def edit_post():
    user = users.get_current_user()
    if not user:
        redirect(users.create_login_url(request.url))
    
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    
    url_id = request.forms.get('url_id')
    
    #return url_id
    application = ndb.Key(urlsafe=url_id).get()
    

    if application.author != user and not users.is_current_user_admin() :
        redirect('/')  
   
    application.content = decode_field(request.forms.get('content'))
    application.author_fn = decode_field(request.forms.get('author_fn'))
    application.author_phone = request.forms.get('author_phone')
    #application.author_bdate = datetime.strptime(request.forms.get('author_bdate'), '%d-%m-%Y')
    #application.author_mail = request.forms.get('author_mail')
    application.author_contacts = decode_field(request.forms.get('author_contacts'))
    application.app_type = request.forms.get('app_type').decode('utf-8')
    application.app_title = decode_field(request.forms.get('app_title'))
    application.app_origin = decode_field(request.forms.get('app_origin'))
    application.city = decode_field(request.forms.get('city'))
    application.timing = request.forms.get('timing')
    #application.app_status = "sent"
    #return application.app_title
    
    try:
        upload = request.files["upload"]
        blob_data = parse_options_header(upload.content_type)[1]
        blob_key =  blob_data["blob-key"]
        if application.test_blob:
            application.test_blob.append(blob_key)
        else:
            application.test_blob = [blob_key]
    except:
        pass
    try:
        rehersal = decode_field(request.forms.get('rehersal'))
    except:
        rehersal = None
    
    if rehersal:
        match = re.search(r"(?:youtube\.com\/\S*(?:(?:\/e(?:mbed))?\/|watch\?(?:\S*?&?v\=))|youtu\.be\/)([a-zA-Z0-9_-]{6,11})", rehersal)
        if match:
            rehersal = match.group(1)
   
    
    if application.rehersals and rehersal:
        application.rehersals.append(rehersal)
    elif rehersal and not application.rehersals:
        application.rehersals = [rehersal]
       
    
    participants_list = []
    
    for i in range(10):
      fullname = request.forms.get("participant_fn_%d" % i)
      nickname = request.forms.get("participant_nickname_%d" % i)
      age = request.forms.get("participant_age_%d" % i)
      fullname = decode_field(fullname)
      nickname = decode_field(nickname)
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
        comment.comment = decode_field(comment_body)
        comment.author = user
        comment.application = url_id
        comment.put()       
    application.put()
    
    

    #return "success"
    #return application
    redirect('/')  

# http://java.dzone.com/articles/upload-and-download-file-mongo
@app.route('/download/<blob_key>')
def download_file(blob_key):
    blob = BlobInfo.get(blob_key)      
    response.headers['X-AppEngine-BlobKey'] = blob_key.decode('utf-8')
    response.headers['Content-Disposition'] = "attachment; filename=%s" % blob.filename
    response.headers['Content-Type'] = blob.content_type
    return response
    
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