from flask import Flask, render_template, flash, redirect, request, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.debug = True

# Config MySQL
app.config['MYSQL_HOST'] = 'HOST' # MySQL Host
app.config['MYSQL_USER'] = 'USER' # MySQL User
app.config['MYSQL_PASSWORD'] = 'PASSWORD' # MySQL password
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
app.config['MYSQL_DB'] = 'DB_NAME' # MySQL Database name

# Initialize MySQL

mysql = MySQL(app)

# Home route
@app.route('/')
def index():
  return render_template('home.html')

# About route
@app.route('/about')
def about():
  return render_template('about.html')

# Get all articles
@app.route('/articles')
def articles():
  cur = mysql.connection.cursor()
  result = cur.execute("SELECT * FROM articles")
  articles = cur.fetchall()

  if result > 0:
    return render_template('articles.html', articles=articles)
  else:
    msg = 'No article found.'
    return render_template('articles.html', msg=msg)
  cur.close()

# Get one Article
@app.route('/article/<string:id>/')
def article(id):
  cur = mysql.connection.cursor()
  result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

  article = cur.fetchone()
  return render_template('article.html', article=article)

# Register Form class
class RegisterForm(Form):
  name = StringField('Name', [validators.Length(min=1, max=50)])
  username = StringField('Username', [validators.Length(min=4, max=25)])
  email = StringField('Email', [validators.Length(min=6, max=50)])
  password = PasswordField('Password', [
    validators.DataRequired(),
    validators.equal_to('confirm', message='Passwords do not match'),
    ])
  confirm = PasswordField('Confirm password')

# Sign up route
@app.route('/register', methods=['GET', 'POST'])
def register():
  form = RegisterForm(request.form)
  if request.method == 'POST' and form.validate():
    name = form.name.data
    email = form.email.data
    username = form.username.data
    password = sha256_crypt.encrypt(str(form.password.data))

    #create cursor
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

    #save to database
    mysql.connection.commit()
    cur.close()

    flash('Registration successfull.', 'success')

    return redirect(url_for('index'))
  return render_template('register.html', form=form)

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    # GET Form-fields
    username = request.form['username']
    password_candidate = request.form['password']

    # Cursor
    cur = mysql.connection.cursor()
     # Get user by username
    
    result = cur.execute('SELECT * FROM users WHERE username = %s', [username])
    if result > 0:
      #Get stored hash
      data = cur.fetchone()
      password = data['password']

      # Compare password
      if sha256_crypt.verify(password_candidate, password):
        session['logged_in'] = True
        session['username'] = username

        flash('You are now logged-in', 'success')
        return redirect(url_for('dashboard'))
      else:
        error = 'Invalid login details'
        return render_template('login.html', error=error)
      cur.close()
    else:
      error = 'User not found.'
      return render_template('login.html', error=error)
  return render_template('login.html')

# Middleware to check of user is logged-in
def is_logged_in(f):
  @wraps(f)
  def wrap(*args, **kwargs):
    if 'logged_in' in session:
      return f(*args, **kwargs)
    else:
      flash('Unauthorized. Please log in', 'danger')
      return redirect(url_for('login'))
  return wrap

# Logout route
@app.route('/logout')
@is_logged_in
def logout():
  session.clear()
  flash('You are now logged out', 'success')
  return redirect(url_for('login'))

# Dashboard route
@app.route('/dashboard')
@is_logged_in
def dashboard():
  cur = mysql.connection.cursor()
  result = cur.execute("SELECT * FROM articles")
  articles = cur.fetchall()

  if result > 0:
    return render_template('dashboard.html', articles=articles)
  else:
    msg = 'No article found.'
    return render_template('dashboard.html', msg=msg)
  cur.close()

# Article for class
class ArticleForm(Form):
  title = StringField('Title', [validators.Length(min=1, max=200)])
  body = TextAreaField('Body', [validators.Length(min=30)])

# Add article method
@app.route('/add_article', methods=['GET', 'POST'])
@is_logged_in
def add_article():
  form = ArticleForm(request.form)
  if request.method == 'POST' and form.validate():
    title = form.title.data
    body = form.body.data

    # Create a cursor
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)", (title, body, session["username"]))
    mysql.connection.commit()

    cur.close()
    flash('Article created successfully', 'success')
    return redirect(url_for('dashboard'))
  return render_template('add_article.html', form=form)


# Edit Article
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
  cur = mysql.connection.cursor()

  result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

  article = cur.fetchone()


  form = ArticleForm(request.form)
  # Populate form field
  form.title.data = article['title']
  form.body.data = article['body']
  if request.method == 'POST' and form.validate():
    title = request.form['title']
    body = request.form['body']

    # Create a cursor
    cur = mysql.connection.cursor()
    cur.execute("UPDATE articles SET title = %s, body = %s WHERE id = %s", (title, body, id))
    mysql.connection.commit()

    cur.close()
    flash('Article edited successfully', 'success')
    return redirect(url_for('dashboard'))
  return render_template('edit_article.html', form = form)

@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
  cur = mysql.connection.cursor()
  cur.execute("DELETE FROM articles WHERE id = %s", [id])

  mysql.connection.commit()
  cur.close()
  flash('Article deleted successfully', 'success')
  return redirect(url_for('dashboard'))
  
  
if __name__ == '__main__':
  app.secret_key='qwertyuiopasdhfkfdldfdf'
  app.run()