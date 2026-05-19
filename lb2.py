import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_session' # Потрібно для сесій користувачів

# Підключення
client = MongoClient('mongodb://localhost:27017/')
db = client.blog_engine

# Колекції (Collections)
users_col = db.users
posts_col = db.posts
categories_col = db.categories
comments_col = db.comments

# --- Ініціалізація категорій (якщо порожньо) ---
if categories_col.count_documents({}) == 0:
    categories_col.insert_many([
        {"name": "Технології", "slug": "tech"},
        {"name": "Життя", "slug": "life"},
        {"name": "Програмування", "slug": "dev"}
    ])

# --- Головна сторінка ---
@app.route('/')
def index():
    # Складний запит: сортування + ліміт
    all_posts = list(posts_col.find().sort("created_at", -1))
    all_categories = list(categories_col.find())
    return render_template('home.html', articles=all_posts, categories=all_categories)

# --- Реєстрація / Логін (Вимога по Users) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_data = {
            "nickname": request.form.get('username'),
            "email": request.form.get('email'),
            "password": generate_password_hash(request.form.get('password'))
        }
        if users_col.find_one({"email": user_data['email']}):
            flash("Такий email вже існує!")
        else:
            users_col.insert_one(user_data)
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = users_col.find_one({"email": request.form.get('email')})
        if user and check_password_hash(user['password'], request.form.get('password')):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['nickname']
            return redirect(url_for('index'))
        flash("Невірні дані")
    return render_template('login.html')

# --- Створення статті ---
@app.route('/publish', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_post = {
            "title": request.form.get('title'),
            "content": request.form.get('content'),
            "category_id": request.form.get('category'),
            "author_id": ObjectId(session['user_id']),
            "author_name": session['user_name'],
            "created_at": datetime.datetime.now()
        }
        posts_col.insert_one(new_post)
        return redirect(url_for('index'))
    
    cats = list(categories_col.find())
    return render_template('create.html', categories=cats)

# --- Перегляд статті та коментарів ---
@app.route('/article/<id>')
def view_post(id):
    post = posts_col.find_one({"_id": ObjectId(id)})
    if not post:
        return "404 Not Found", 404
    
    # Запит коментарів для конкретної статті
    post_comments = list(comments_col.find({"post_id": ObjectId(id)}).sort("date", 1))
    return render_template('article.html', article=post, comments=post_comments)

# --- Додавання коментаря ---
@app.route('/article/<id>/comment', methods=['POST'])
def add_comment(id):
    comment = {
        "post_id": ObjectId(id),
        "author": request.form.get('author') or "Анонім",
        "text": request.form.get('text'),
        "date": datetime.datetime.now()
    }
    if comment['text']:
        comments_col.insert_one(comment)
    return redirect(url_for('view_post', id=id))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)