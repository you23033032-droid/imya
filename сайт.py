from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_change_me'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    balance = db.Column(db.Float, default=0.0)

class Novel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('marketplace'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        if User.query.filter_by(username=username).first():
            flash('Username exists')
            return render_template('register.html')
        user = User(username=username, password_hash=password)
        db.session.add(user)
        db.session.commit()
        flash('Registered')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            session['user_id'] = user.id
            flash('Logged in')
            return redirect(url_for('balance'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/balance')
def balance():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    return render_template('balance.html', user=user)

@app.route('/balance/topup', methods=['POST'])
def topup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    amount = float(request.form['amount'])
    user = User.query.get(session['user_id'])
    user.balance += amount
    db.session.commit()
    flash(f'Top-up {amount} successful')
    return redirect(url_for('balance'))

@app.route('/balance/withdraw', methods=['POST'])
def withdraw():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    amount = float(request.form['amount'])
    user = User.query.get(session['user_id'])
    if user.balance >= amount:
        user.balance -= amount
        db.session.commit()
        flash(f'Withdrawal {amount} successful')
    else:
        flash('Insufficient balance')
    return redirect(url_for('balance'))

@app.route('/marketplace')
def marketplace():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    novels = Novel.query.all()
    return render_template('marketplace.html', novels=novels)

@app.route('/sell', methods=['GET', 'POST'])
def sell():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = float(request.form['price'])
        content = request.form['content']
        novel = Novel(title=title, description=description, price=price, seller_id=session['user_id'], content=content)
        db.session.add(novel)
        db.session.commit()
        flash('Novel listed for sale')
        return redirect(url_for('marketplace'))
    return render_template('sell.html')

@app.route('/buy/<int:novel_id>', methods=['POST'])
def buy(novel_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    novel = Novel.query.get(novel_id)
    if not novel:
        flash('Novel not found')
        return redirect(url_for('marketplace'))
    buyer = User.query.get(session['user_id'])
    if buyer.balance >= novel.price:
        buyer.balance -= novel.price
        seller = User.query.get(novel.seller_id)
        seller.balance += novel.price
        db.session.commit()
        flash(f'Bought "{novel.title}" for {novel.price}')
    else:
        flash('Insufficient balance')
    return redirect(url_for('marketplace'))

if __name__ == '__main__':
    app.run(debug=True)

