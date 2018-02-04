from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
import json
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import pymysql
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'aryan-rds-movie-task.ca7x3oxpwgii.us-east-1.rds.amazonaws.com'
app.config['MYSQL_USER'] = 'aryan'
app.config['MYSQL_PASSWORD'] = 'qwerty95'
app.config['MYSQL_DB'] = 'aryanDb'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)




# About
@app.route('/about')
def about():
    return render_template('about.html')


# movies
@app.route('/movies',methods=['GET', 'POST'])
def movies():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM movie_info")
    movies = cur.fetchall()
    # displays a table of movies
    if request.method == 'GET':

        if result > 0:
            return render_template('home.html', result=movies)
        else:
            msg = 'Server Down'
            return render_template('home.html', msg=msg)
        cur.close()
    #  user can search a movie by name or by genre
    elif request.method == 'POST':
        cur = mysql.connection.cursor()
        if 'name' in request.form:
            name = str(request.form['name'])
            result = cur.execute("SELECT * FROM movie_info WHERE name = %s", [name])
            movie = cur.fetchone()
            name=movie["name"]
            director=movie["director"]
            imdb_score=movie["imdb_score"]
            popularity=movie["popularity"]
            genre=movie["genre"]
            idn=movie["id"]
            cur.close()
            return render_template('search.html',id=idn,name=name,director=director,imdb_score=imdb_score,popularity=popularity,genre=genre)
        if 'genre' in request.form:
            genreInput = str(request.form['genre'])
            db_fetched_data=json.dumps(movies)
            json_data = json.loads(db_fetched_data)
            search_res=[]
            for i in range(0,len(json_data)):
                this_value=json_data[i]
                director=this_value['director']
                genre=this_value['genre']
                genre=str(genre)
                # genre= genre.replace("u","").replace("'","")
                genre=[str(i) for i in genre.strip('[]').split(',')]
                imdb_score=this_value['imdb_score']
                name=this_value['name']
                popularity=this_value['popularity']
                search_in_genre=process.extractOne(genreInput, genre)
                score=search_in_genre[1]
                if score>=90:
                    data={
                    "name":name,
                    "imdb_score":imdb_score,
                    "popularity":popularity,
                    "director":director,
                    "genre":genre
                    }
                    search_res.append(data)
            return render_template('home.html',result=tuple(search_res))

    return render_template('home.html', result=movies)



# Register Form Class
class RegisterForm(Form):
    role = StringField('role', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/admin/register', methods=['GET', 'POST'])
def register():
    host="aryan-rds-movie-task.ca7x3oxpwgii.us-east-1.rds.amazonaws.com"
    port=3306
    user="aryan"
    dbname="aryanDb"
    password="qwerty95"
    form = RegisterForm(request.form)
    if request.method == 'POST':   # and form.validate():
        role = form.role.data
        email = form.email.data
        username = form.username.data
        password = sha256_crypt.encrypt(str(form.password.data))
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO users (role, email, username, password) VALUES(%s, %s, %s, %s)", (role, email, username, password))
            mysql.connection.commit()
            cursor.close()
            flash('You are now registered and can log in', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            print str(e)
 
    return render_template('register.html', form=form)


# User login
@app.route('/admin/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        cursor=mysql.connection.cursor()
        
        # conn=pymysql.connect(host,user=user,port=port,passwd=password,db=dbname)

        # Get user by username
        result = cursor.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
        # Get stored hash
            data = cursor.fetchone()
            password = data['password']

        # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
            # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cursor.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/admin/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

# Dashboard
@app.route('/admin/dashboard')
@is_logged_in
def dashboard():
    try:
        cursor=mysql.connection.cursor()

        sqlQ="SELECT * FROM `movie_info`"
        check=cursor.execute(sqlQ)
        result=cursor.fetchall()
        mysql.connection.commit()
        cursor.close()


    except Exception as e:
        print str(e)


    if check > 0:
        return render_template('dashboard.html', result=result)
    else:
        msg = 'Nothing Found'
        return render_template('dashboard.html', msg=msg)


# Movie Form Class
class MovieForm(Form):
    name = StringField('name', [validators.Length(min=1, max=20)])
    director = StringField('director', [validators.Length(min=30)])
    genre = StringField('genre',[validators.Length(max=255)])
    imdb_score = StringField('imdb_score',[validators.Length(max=4)])
    popularity = StringField('popularity',[validators.Length(max=5)])


@app.route('/admin/add_movie', methods=['GET', 'POST'])
@is_logged_in
def add_movie():
    form = MovieForm(request.form)
    if request.method == 'POST':# and form.validate():
        name = form.name.data
        director = form.director.data
        genre = form.genre.data
        imdb_score = form.imdb_score.data
        popularity = form.popularity.data
        # Create Cursor
        print "getting here"
        # Execute
        try: 
            cursor=mysql.connection.cursor()

            print "check for all",popularity,director,imdb_score,name,genre
            cursor.execute("INSERT INTO movie_info (popularity,director,imdb_score,name,genre) VALUES( %s, %s, %s, %s, %s)",(popularity,director,imdb_score,name,genre))
            mysql.connection.commit()
            cursor.close()
            flash('Movie added to db', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            print str(e)

    return render_template('add_movie.html', form=form)


# Edit Movie
@app.route('/admin/edit_movie/<name>', methods=['GET', 'POST'])
@is_logged_in
def edit_movie(name):
    # Create cursor
    cur = mysql.connection.cursor()


    result = cur.execute("SELECT * FROM movie_info WHERE name = %s", [name])

    movie = cur.fetchone()
    cur.close()
    # Get form
    form = MovieForm(request.form)
    form.name.data = movie['name']
    form.director.data = movie['director']
    form.genre.data = movie['genre']
    form.imdb_score.data = movie['imdb_score']
    form.popularity.data = movie['popularity']
    if request.method == 'POST': # and form.validate():
        name = request.form['name']
        director = request.form['director']
        genre =request.form['genre']
        imdb_score=request.form['imdb_score']
        popularity=request.form['popularity']
        # Create Cursor
        cur = mysql.connection.cursor()
        app.logger.info(name)
        # Execute
        cur.execute ("UPDATE movie_info SET name=%s, imdb_score=%s, popularity=%s, genre=%s, director=%s WHERE name=%s",(name, imdb_score, popularity, genre, director, name))
        # Commit to DB
        mysql.connection.commit()

        #Close connection
        cur.close()

        flash('Movie Info Updation', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_movie.html', form=form)

# Delete Article
@app.route('/admin/delete_movie/<name>', methods=['POST'])
@is_logged_in
def delete_movie(name):
    # Create cursor
    cur = mysql.connection.cursor()

    # Execute
    cur.execute("DELETE FROM movie_info WHERE name = %s", [name])

    # Commit to DB
    mysql.connection.commit()

    #Close connection
    cur.close()

    flash('Movie Deletion', 'success')

    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)