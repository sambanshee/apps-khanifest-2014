import bottle
from bottle import *

app = Bottle()

@app.route('/')
def DisplayForm():
    message = 'Hello World'
    #output = template('templates/home', data = message)
    return message


@app.error(403)
def Error403(code):
    return 'Get your codes right dude, you caused some error!'

@app.error(404)
def Error404(code):
    return 'Stop cowboy, what are you trying to find?'

run(app=app, server='gae')