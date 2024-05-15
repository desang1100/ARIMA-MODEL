from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import os
import mysql.connector
from db import create_db
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create database and tables if they don't exist
create_db()

# MYSQL configurations
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'db_rice'

# Connect to MySQL
mysql = mysql.connector.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    password=app.config['MYSQL_PASSWORD'],
    database=app.config['MYSQL_DB']
)

# Set the directory where the data file is located
DATA_DIR = 'data'

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'loggedin' not in session:
            flash('Please login to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def upload_file():
    return render_template('arima.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cursor = mysql.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s AND password = %s', (email, password,))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['email'] = account['email']
            return redirect(url_for('profile'))
        else:
            msg = 'Incorrect email/password'
    return render_template('login.html', msg=msg)

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('email', None)
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    msg = ''
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        mname = request.form['mname']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.cursor(dictionary=True)
        cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists!'
        elif not email or not password:
            msg = 'Please fill out the form.'
        else:
            cursor.execute('INSERT INTO users (email, fname, mname, lname, password) VALUES (%s, %s, %s, %s, %s)', (email, fname, mname, lname, password))
            mysql.commit()
            msg = 'You have successfully signed up!'
    return render_template('signup.html', msg=msg)

@app.route('/profile')
@login_required
def profile():
    return render_template('arima.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if request.method == 'POST':
        file = request.files['file']
        file_path = os.path.join(DATA_DIR, file.filename)
        file.save(file_path)
        
        df = pd.read_csv(file_path)
        
        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # ARIMA model
        def arima_model(series):
            model = ARIMA(series, order=(5,1,0))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=1)
            return forecast.item()

        # Predict next month's prices
        next_month = pd.Timestamp(df.index[-1]) + pd.DateOffset(months=2)
        next_month_prices = {}

        for column in df.columns:
            forecast = arima_model(df[column])
            next_month_prices[column] = forecast

        forecast_df = pd.DataFrame(list(next_month_prices.items()), columns=['Type of Rice', 'Forecasted Price'])
        
        # Plot original data and forecasted values
        plt.figure(figsize=(10, 6))
        for column in df.columns:
            plt.plot(df.index, df[column], label=column)

        for column in next_month_prices:
            label = f'Forecasted {column}'
            plt.scatter(next_month, next_month_prices[column], color='red', label=label)

        plt.title("Rice Prices Forecast")
        plt.xlabel("Date")
        plt.ylabel("Price")
        plt.legend()
        plt.grid(True)
        
        # Convert plot to base64 encoded image
        img_data = BytesIO()
        plt.savefig(img_data, format='png')
        img_data.seek(0)
        img_base64 = base64.b64encode(img_data.getvalue()).decode()

        # Render the template with results
        return render_template('results.html', next_month=next_month, forecast_df=forecast_df.to_html(index=False, classes="table table-bordered table-striped"), plot=img_base64)

@app.route('/predict_years', methods=['POST'])
@login_required
def predict_years():
    if request.method == 'POST':
        file = request.files['file']
        file_path = os.path.join(DATA_DIR, file.filename)
        file.save(file_path)
        
        df = pd.read_csv(file_path)
        
        # Convert 'Date' column to datetime
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        
        # ARIMA model
        def arima_model(series):
            model = ARIMA(series, order=(5,1,0))
            model_fit = model.fit()
            forecast = model_fit.forecast(steps=12)  # Forecast for the entire year
            return forecast

        # Predict prices for 2025, 2026, and 2027
        forecast_years = [2025, 2026, 2027]
        for year in forecast_years:
            forecast_df = pd.DataFrame()
        
            for column in df.columns:
                forecast = arima_model(df[column])
                forecast_df[column] = forecast

            # Plot original data and forecasted values
            plt.figure(figsize=(10, 6))
            for column in df.columns:
                plt.plot(df.index, df[column], label=column)

            for column in forecast_df.columns:
                plt.plot(pd.date_range(start=f'{year}-01-01', periods=12, freq='MS'), forecast_df[column], linestyle='dashed', label=f'Forecasted {column}')

            plt.title(f"Rice Prices Forecast for {year}")
            plt.xlabel("Date")
            plt.ylabel("Price")
            plt.legend()
            plt.grid(True)
            
            # Convert plot to base64 encoded image
            img_data = BytesIO()
            plt.savefig(img_data, format='png')
            img_data.seek(0)
            img_base64 = base64.b64encode(img_data.getvalue()).decode()

            # Generate HTML table
            html_table = forecast_df.to_html(index=False, classes="table table-bordered table-striped")

            # Render the template with results
            return render_template('results_yearly.html', year=year, forecast_df=html_table, plot=img_base64)

if __name__ == '__main__':
    app.run(debug=True)
