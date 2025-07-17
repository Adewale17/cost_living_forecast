from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import joblib
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # change this in production

# Configure DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite3'
db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))  # Link to User table
    gender = db.Column(db.String(10))
    year = db.Column(db.String(20))
    lifestyle = db.Column(db.String(20))
    accommodation_type = db.Column(db.String(20))
    finance_sources = db.Column(db.String(100))
    earn_income = db.Column(db.String(5))
    predicted_cost = db.Column(db.Float)


# Load model and data
model = joblib.load(os.path.join('model', 'model.pkl'))
df = pd.read_excel(os.path.join('data', 'undergraduate_data.xlsx'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, request.form['password']):
            session['user'] = user.name
            flash('Login successful', 'success')
            return redirect(url_for('forecast'))
        else:
            flash('Invalid credentials', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully', 'info')
    return redirect(url_for('home'))

@app.route('/forecast', methods=['GET', 'POST'])
def forecast():
    if 'user' not in session:
        flash('Login required to access forecast', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        form_data = {
            'Gender': request.form['gender'],
            'Year': request.form['year'],
            'Lifestyle': request.form['lifestyle'],
            'AccommodationType': request.form['accommodation'],
            'FinanceSources': request.form['finance'],
            'EarnIncome': request.form['income']
        }

        # Find similar users
        matches = df[
            (df['Gender'] == form_data['Gender']) &
            (df['Year'] == form_data['Year']) &
            (df['Lifestyle'] == form_data['Lifestyle']) &
            (df['AccommodationType'] == form_data['AccommodationType']) &
            (df['FinanceSources'] == form_data['FinanceSources']) &
            (df['EarnIncome'] == form_data['EarnIncome'])
        ]

        numeric_cols = [
            'Age', 'Rent', 'Feeding', 'TransportCost', 'Textbooks', 'Insurance',
            'Medical', 'SubCost', 'Social', 'OtherExpenses', 'YearlyIncome', 'AidAmount'
        ]

        # Use averages of matching records or full dataset
        averages = matches[numeric_cols].mean().to_dict() if not matches.empty else df[numeric_cols].mean().to_dict()
        full_input = {**averages, **form_data}

        # Predict cost
        X = pd.DataFrame([full_input])
        prediction = model.predict(X)[0]

        # Save to DB
        user = User.query.filter_by(name=session['user']).first()
        new_prediction = Prediction(
            user_id=user.id,
            gender=form_data['Gender'],
            year=form_data['Year'],
            lifestyle=form_data['Lifestyle'],
            accommodation_type=form_data['AccommodationType'],
            finance_sources=form_data['FinanceSources'],
            earn_income=form_data['EarnIncome'],
            predicted_cost=prediction
        )
        db.session.add(new_prediction)
        db.session.commit()

        result = f" Based on your profile, your forecasted yearly cost is: ₦{prediction:,.2f}"
        return render_template('forecast.html', prediction=result)

    return render_template('forecast.html')

@app.route('/history')
def history():
    if 'user' not in session:
        flash('Login required to access history', 'warning')
        return redirect(url_for('login'))

    user = User.query.filter_by(name=session['user']).first()
    predictions = Prediction.query.filter_by(user_id=user.id).all()
    return render_template('history.html', predictions=predictions)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    print("🚀 Starting Flask App...")
    app.run(debug=True)