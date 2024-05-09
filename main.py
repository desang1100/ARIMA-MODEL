from flask import Flask, render_template, request
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from tabulate import tabulate
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import os

app = Flask(__name__)

# Set the directory where the data file is located
DATA_DIR = 'data'

@app.route('/')
def upload_file():
    return render_template('arima.html')

@app.route('/predict', methods=['POST'])
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

        #-----------------YEARLY------------------------------------------------------------------------------------------------------>>>>>>>>
        
        
        return render_template('results.html', next_month=next_month, forecast_df=forecast_df.to_html(index=False), plot=img_base64)
    
@app.route('/predict_years', methods=['POST'])
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

            # Display forecasted prices in a table
            print(f"\nForecasted prices for {year}:")
            print(tabulate(forecast_df, headers='keys', tablefmt='grid', showindex=False))

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

            # Pass the plot as base64 encoded image to the template
            return render_template('results_yearly.html', year=year, forecast_df=forecast_df.to_html(index=False), plot=img_base64)
        

if __name__ == '__main__':
    app.run(debug=True)
