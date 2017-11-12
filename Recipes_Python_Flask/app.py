from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from flask_wtf.file import FileField, FileRequired
from passlib.hash import sha256_crypt
from functools import wraps
from werkzeug.utils import secure_filename
import os


app = Flask(__name__)
app.secret_key = '<!SecreT!/>'

#Database config
app.config['MYSQL_HOST'] = 'eu-cdbr-west-01.cleardb.com'
app.config['MYSQL_USER'] = 'b7f5d06a8743d6'
app.config['MYSQL_PASSWORD'] = 'b658456f'
app.config['MYSQL_DB'] = 'heroku_f3f2ab76077d6b8'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
#init MYSQL
mysql = MySQL(app)


@app.route('/')
def index():
    cursor = mysql.connection.cursor()
    #get recepies
    result = cursor.execute("SELECT * FROM recepies")
    recepies = cursor.fetchall()

    if result > 0:
        cursor.close()
        return render_template('index.html', recepies=recepies)
    else:
        cursor.close()
        return render_template('index.html')

    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

class RegisterForm(Form):
    username = StringField('Username', [validators.Length(min=3, max=30)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
    validators.DataRequired(),
    validators.EqualTo('confirm', message='Password do not match')
    ])
    confirm = PasswordField('Confirm Password')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)

    if request.method == 'POST' and form.validate():
        username = form.username.data
        email = form.email.data

        password = sha256_crypt.encrypt(str(form.password.data))
        #Create cursor
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO user(username, email, password) VALUES(%s, %s, %s)",(username, email, password))

        #commit to DB
        mysql.connection.commit()

        #close connection
        cursor.close()

        flash('You are now registered and log in', 'success')
        return redirect(url_for('index'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        entered_password = request.form['password']

        #Database connection
        cursor = mysql.connection.cursor()

        #Get user by username
        result = cursor.execute("SELECT * FROM user WHERE username = %s", [username])
        if result > 0:
            #Get hashed password
            data = cursor.fetchone()
            password = data['password']

            #Compere passwords
            if sha256_crypt.verify(entered_password, password):
                session['logged_in'] = True
                session['username'] = username

                #Close connection
                cursor.close()
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                #Close connection
                cursor.close()
                error = "Invalid Login"
                return render_template('login.html', error=error)
        else:
            #Close connection
            cursor.close()
            error = "Invalid Login"
            return render_template('login.html', error=error)

    return render_template('login.html')

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized, Please login", 'danger')
            return redirect(url_for('login'))
    return wrap

@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for('login'))

@app.route('/dashboard')
@is_logged_in
def dashboard():
    #Cursor
    cursor = mysql.connection.cursor()

    #get recepies
    result = cursor.execute("SELECT * FROM recepies WHERE author = %s", [session['username']])
    recepies = cursor.fetchall()

    if result > 0:
        cursor.close()
        return render_template('dashboard.html', recepies=recepies)
    else:
        cursor.close()
        msg = 'No Recepies Found'
        return render_template('dashboard.html', msg=msg)

class RecepieForm(Form):
    title = StringField('Title', [validators.Length(min=3, max=120)])
    ingredients = TextAreaField('Ingredients', [validators.Length(min=10)])
    directions = TextAreaField('Directions', [validators.Length(min=10)])

#allowed file extendsions
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

#checking if extendsion is allowed
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#TODO validate img
@app.route('/add_recepie', methods=['GET', 'POST'])
@is_logged_in
def add_recepie():
    form = RecepieForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        ingredients = form.ingredients.data
        directions = form.directions.data
        files = request.files['file']

        #file upload folder
        target =  'static/images/'

        #check if folder exists
        if not os.path.isdir(target):
            os.mkdir(target)

        pic_path = None
        #check if picture was upload and extendsion allowed
        if files.filename != '' and allowed_file(files.filename):
            filename = secure_filename(files.filename)
            files.save(os.path.join(target, filename))
            pic_path = filename

        #cursor
        cursor = mysql.connection.cursor()

        #execute
        cursor.execute("INSERT INTO recepies(title, ingredients, directions, author, picture_path) VALUES(%s, %s, %s, %s, %s)",
            (title, ingredients, directions, session['username'], pic_path))

        #commit to database
        mysql.connection.commit()

        #close connection
        cursor.close()

        if files.filename == '':
            flash('Recepie updated without an image', 'success')
        elif files.filename != '' and not allowed_file(files.filename):
            flash('Recepie Updated but image extension is not allowed', 'danger')
        else:
            flash('Recepie Updated', 'success')

        return redirect(url_for('dashboard'))
    return render_template('add_recepie.html', form=form)

@app.route('/recepies')
def recepies():
    #Cursor
    cursor = mysql.connection.cursor()

    #get recepies
    result = cursor.execute("SELECT * FROM recepies")
    recepies = cursor.fetchall()

    if result > 0:
        cursor.close()
        return render_template('recepies.html', recepies=recepies)
    else:
        cursor.close()
        msg = 'No Recepies Found'
        return render_template('recepies.html', msg=msg)

@app.route('/recepie/<string:id>/')
def recepie(id):
        #Cursor
        cursor = mysql.connection.cursor()

        #get recepies
        result = cursor.execute("SELECT * FROM recepies WHERE id = %s", [id])
        recepie = cursor.fetchone()

        return render_template('recepie.html', recepie=recepie)


#TODO validate img
@app.route('/edit_recepie/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_recepie(id):
    # Create cursor
    cursor = mysql.connection.cursor()

    # Get article by id
    result = cursor.execute("SELECT * FROM recepies WHERE id = %s", [id])
    recepie = cursor.fetchone()
    cursor.close()

    if recepie['author'] != session['username']:
        flash('Sorry, you cannot edit that recepie', 'danger')
        return redirect(url_for('dashboard'))

    # Get form
    form = RecepieForm(request.form)

    # Populate article form fields
    form.title.data = recepie['title']
    form.ingredients.data = recepie['ingredients']
    form.directions.data = recepie['directions']

    #save img to delate after new submit
    img_to_erase = recepie['picture_path']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        ingredients = request.form['ingredients']
        directions = request.form['directions']
        files = request.files['file']

        #file upload to folder
        target =  'static/images/'

        #check if folder exists
        if not os.path.isdir(target):
            os.mkdir(target)

        pic_path = None
        #check if picture was upload and extension is allowed
        if files.filename != '' and allowed_file(files.filename):
            filename = secure_filename(files.filename)
            files.save(os.path.join(target, filename))
            pic_path = filename

        #delate old img before db commit
        if img_to_erase != None:
            try:
                os.remove(os.path.join(target, img_to_erase))
            except OSError as err:
                app.logger.info("CANNOT ERASE OR FIND THE FILE")

        # Create Cursor
        cursor = mysql.connection.cursor()

        # Execute
        cursor.execute ("UPDATE recepies SET title=%s, ingredients=%s, directions=%s, picture_path=%s WHERE id=%s",
            (title, ingredients, directions, pic_path, id))

        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cursor.close()

        #if user didn't upload image
        if files.filename == '':
            flash('Recepie updated without an image', 'success')
        elif files.filename != '' and not allowed_file(files.filename):
            flash('Recepie Updated but image extension is not allowed', 'danger')
        else:
            flash('Recepie Updated', 'success')

        return redirect(url_for('dashboard'))
    return render_template('edit_recepie.html', form=form)

@app.route('/delete_recepie/<string:id>', methods=['POST'])
@is_logged_in
def delete_recepie(id):
    # Create cursor
    cursor = mysql.connection.cursor()

    # Execute
    cursor.execute("DELETE FROM recepies WHERE id = %s", [id])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cursor.close()

    flash('Recepie Deleted', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
