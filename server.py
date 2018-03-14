from flask import Flask, render_template, redirect, request, session, flash, send_from_directory
# from flask_bcrypt import bcrypt, check_password_hash, generate_password_hash
from database import MySQLConnector
import bcrypt
import re
import datetime
app = Flask(__name__)

app.secret_key = 'SuperSECRETkey'
emailRegex = re.compile("(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")
mysql = MySQLConnector(app, 'mydb')

@app.route('/')
def index():
    try:
        if session['user_id']:
            return redirect('/homepage')
    except:
        return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    errors = []
    email = request.form['email']
    password = request.form['password']
    query = "SELECT * FROM users WHERE email = :email"
    data = {'email': email}
    user = mysql.query_db(query, data)

    if len(user) == 0:
        errors.append("Please Register First")
        return render_template('index.html', errors=errors)
    else:
        if bcrypt.checkpw(password.encode(), user[0]['password'].encode()):
            session['user_id'] = user[0]['idusers']
            return redirect('/homepage')
        else:
            errors.append("Email and Password Combination Incorrect")
            return render_template("index.html", errors=errors)

@app.route("/user/logout")
def logout():
    session.clear()
    return redirect("/")
        
        

@app.route('/registration')
def registration():
    return render_template('registration.html')


@app.route('/register', methods=['POST'])
def register():
    errors = []
    first_name = request.form['first_name']
    last_name = request.form['last_name']
    password = request.form['password']
    email = request.form['email']

    if len(first_name) < 1: 
        errors.append('Missing First Name')
    if len(last_name) < 1:
        errors.append('Missing Last Name')
    if len(email) < 1:
        errors.append('Missing email')
    if not re.match(emailRegex, email):
        errors.append('Incorrect Email')
    if request.form['password_confirmation'] != password:
        errors.append('Passwords do not match')

    email_check = "SELECT email FROM users WHERE users.email = :email LIMIT 1"
    query_data = {'email': email}
    user = mysql.query_db(email_check, query_data)
    if len(user) != 0:
        print (user)
        errors.append('Email is already taken')
    if len(errors) > 0:
        return render_template('registration.html', errors=errors)
    
    else:
        hashpassword = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt())
        insert_query = "INSERT INTO users (first_name, last_name, email, password) VALUES (:first_name, :last_name, :email, :password)"

        query_data = { 'first_name': first_name, 'last_name': last_name, 'email': email, 'password': hashpassword}
        new_user = mysql.query_db(insert_query, query_data)
        
        session['user_id'] = new_user
        
        
    return redirect('/homepage')

@app.route('/homepage')
def homepage():
    try: 
        user = session['user_id']
        data = {'user': user}
        tentative = mysql.query_db("SELECT * FROM tasks WHERE current_state = 1")
        process = mysql.query_db("SELECT * FROM tasks WHERE current_state = 2")
        complete = mysql.query_db("SELECT * FROM tasks WHERE current_state = 3")
        discard = mysql.query_db("SELECT * FROM tasks WHERE current_state = 4")
        return render_template('homepage.html', tentative=tentative, process=process, complete=complete, discard=discard )
    except:
        flash("You need to be logged in to use that feature")
        return redirect("/")


@app.route('/add_task')
def create_task_page():
    return render_template('add_task.html')

@app.route('/change_task/<task>', methods=['POST'])
def change_task(task):
    
    if request.form['selected_task'] == "discards":
        choice = 4
    elif request.form['selected_task'] == "completes":
        print ('checkaaa')
        choice = 3
    elif request.form['selected_task'] == "processes":
        choice = 2
    else:
        choice = 1
    query = "UPDATE tasks SET current_state = :choice WHERE idtasks = :task"
    data = {
        'choice': choice,
        'task': task,
    }
    mysql.query_db(query, data)
    return redirect('/homepage')

        

# 1 = tentative
# 2 = process
# 3 = complete
# 4 = discard

@app.route('/task/create', methods=["POST"])
def create_task():
    query = "INSERT INTO tasks (title, description, users_idusers, current_state) VALUES (:title, :description, :users_idusers, :current_state)"
    data = {'title': request.form['title'],
        'description': request.form['description'],
        'users_idusers': session['user_id'],
        'current_state': 1,}   
   
    new_task = mysql.query_db(query, data)
    
    return redirect ('/homepage')

@app.route('/task/view/<task>')
def view_task(task):
    task_querried = mysql.query_db("SELECT * FROM tasks WHERE idtasks = :task", {'task': task})
    task = task_querried[0]
    time = datetime.datetime.today().replace(microsecond=0)
    
    time_from_creation = (time - task['created_at'])
    time_from_update = (time - task['updated_at'])
    return render_template('view_task.html', task=task, tupdate=time_from_update, tcreated=time_from_creation)

@app.route('/user/account')
def user_show():
    user = mysql.query_db("SELECT * FROM users WHERE idusers = :user", {"user": session['user_id']})
    user = user[0]
    return render_template('user_show.html', user=user)

    

@app.route("/user/update", methods=["POST"])
def update():
    user_id = session['user_id']
    # find which areas are filled and apply those migrations
    # design the query based around the given criteria
    updates = []
    errors = []
    check_user = mysql.query_db("SELECT * FROM users WHERE idusers = :user",{'user': session['user_id']})
    if not bcrypt.checkpw(request.form['password'].encode(), check_user[0]['password'].encode()):
        errors.append("Incorrect Password")
    
    if request.form['first_name']:
        if (len(request.form['first_name']) > 1):
            first_name = request.form['first_name']
            updates.append(first_name)
        else:
            errors.append('First name must be greater than 1')

    if request.form['last_name']:
        if (len(request.form['last_name']) > 1):
            last_name = request.form['last_name']
            updates.append(last_name)
        else:
            errors.append("Last Name Must be greater than 1 ")
            
    if request.form['email']:
        email_check = mysql.query_db("SELECT * FROM users WHERE email = :email", {'email':request.form['email']})
        if (len(email_check)) > 0:
            if re.match(emailRegex, request.form['email']):
                email = request.form['email']
                updates.append(email)
            else:
                errors.append("Incorrect Email Format")
        else:
            errors.append("Email Already Exists")

    if request.form['new_password']:
        if request.form['password_confirmation'] == request.form['new_password']:
            password = bcrypt.hashpw(request.form['password'].encode(), bcrypt.gensalt())
            updates.append(password)
        else:
            errors.append('Passwords do no match')
    
    if errors:
        flash(errors)
        return redirect("/user/account")
    
    if (len(updates) > 0):

        query_columns = []
        data = {'users': user_id}
        for i in updates:
            try:
                if first_name:
                    query_columns.append('first_name = :first_name')
                    data['first_name'] = first_name
            except:
                pass
            try:
                if last_name:
                    query_columns.append('last_name = :last_name')
                    data['last_name'] = last_name
            except:
                pass
            try:
                if email:
                    query_columns.append('email = :email')
                    data['email'] = email
            except:
                pass
            try:
                if password:
                    query_columns.append('password = :password')
                    data['password'] = password
            except:
                pass
        query = "UPDATE users SET {} WHERE idusers = :users".format(",".join(query_columns))
        update = mysql.query_db(query, data)
        return redirect('/user/account')
    else:
        return redirect('/user/account')

@app.route('/task/delete/<task>', methods=['POST'])
def delete_task(task):
    user_id = session['user_id']
    query = "DELETE FROM tasks WHERE idtasks = :task AND users_idusers = :user"
    data = {
        'task':task,
        'user':user_id,
    }
    return redirect('/homepage')
app.run(debug=True)