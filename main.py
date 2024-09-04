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
from flask import send_file
from io import StringIO 

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create database and tables if they don't exist
create_db()
from flask_mysqldb import MySQLdb

# MySQL Configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = ''
DB_NAME = 'db_rice'
cred = {
    'host': DB_HOST,
    'user': DB_USER,
    'pw': DB_PASSWORD,
    'db_name': DB_NAME
}

# Set the directory where the data file is located
DATA_DIR = 'data'

def login_required(route):
    @wraps(route)
    def wrap(*args, **kwargs):
        if 'logged' in session:
            return route(*args, **kwargs)
        else:
            return redirect(url_for("login"))
    return wrap

def connection():
    try:
        conn = MySQLdb.connect(host=cred['host'], user=cred['user'], password=cred['pw'], db=cred['db_name'])
        return conn
    except Exception as e:
        print("Error connecting to database:", e)
        return None

@app.route('/sign')
def sign():
    return render_template('signup.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'logged' in session:
        return redirect(url_for('profile'))
    else:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            conn = connection()
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
                user = cur.fetchone()
            conn.close()

            if user:
                session['logged'] = True
                session['email'] = user[1]
                session['fname'] = user[2]
                return redirect(url_for('profile'))
            else:
                flash('Invalid email or password')
                return redirect(url_for('login'))
    return render_template('login.html')



@app.route("/logout")
@login_required
def logout():
    session.pop('logged', None)
    session.pop('email', None)
    session.pop('fname', None)
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        mname = request.form['mname']
        email = request.form['email']
        password = request.form['password']

        conn = connection()
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE email = %s", [email])
            account = cur.fetchone()
            if account:
                flash("Email already registered!")
                return redirect(url_for("signup"))
            else:
                cur.execute("INSERT INTO users VALUES(NULL, %s, %s, %s, %s, %s)", (email, fname, mname, lname, password))
                conn.commit()
                flash("Account created successfully!")
                return redirect(url_for("login"))
        conn.close()
    return render_template('signup.html')



@app.route('/profile')
@login_required
def profile():
    fname = session.get('fname', '')
    return render_template('arima.html', fname=fname)



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

        # Convert forecast_df to string format
        forecast_df_str = forecast_df.astype(str)

        # Render the template with results and forecast_df_str
        return render_template('results.html', next_month=next_month, forecast_df=forecast_df_str, plot=img_base64)



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
