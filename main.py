#flask libraries
from flask import Flask, render_template, request, session
from flask import  redirect, url_for, flash
import sqlite3
#data collection libraries
import serial
import csv
import time
import threading
# model libraries
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import SimpleRNN, Dense
import matplotlib.pyplot as plt
name= "defalut"
app = Flask(__name__)
app.secret_key = 'supersecretkey'

collecting_data = False
arduino_port = '/dev/cu.usbserial-0001'  # Change this to your Arduino port
baud_rate = 115200
output_file = '/Users/charankurukuntla/ad_test/sensor_data.csv'

@app.route('/')
def home(): 
    return render_template('home.html')


@app.route('/tolog')
def sign(): 
    return render_template('login.html')

@app.route('/tosign')
def log(): 
    return render_template('signup.html')


@app.route('/out')
def out(): 
    return render_template('home.html')

@app.route('/index')
def index(): 
    return render_template('index.html')



#navigating from home page to collecting page function
@app.route('/collecting')
def collecting():
    return render_template('collecting.html')



#sign up data function
@app.route('/sign-up', methods=['POST'])
def signup():
    import sqlite3
    name = request.form['new-username']
    email = request.form['email']
    password = request.form['new-password']
    proffession= request.form['proffession']
    degree = request.form['degree']
    
    # Connect to the SQLite database
    connection = sqlite3.connect("my_database.db")
    cursor = connection.cursor()
    #create table with attribues
    #cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, proffession TEXT, degree TEXT)")
    cursor.execute("SELECT * FROM users WHERE name = ? ", (name,))
    existing_user = cursor.fetchone()
    if existing_user:
            return render_template('signup.html')
    
    cursor.execute("INSERT INTO users (name, email,password, proffession, degree) VALUES (?, ?, ?, ?, ?)", (name, email,password,proffession,degree))   
    # Commit the changes and close the connection
    connection.commit()
    connection.close()
    return render_template('login.html')

#lo@app.route('/login', methods=['GET', 'POST'])
# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Connect to the database and verify credentials
        connection = sqlite3.connect("my_database.db")
        cursor = connection.cursor()
        
        # Fetch user with matching username and password
        cursor.execute("SELECT * FROM users WHERE name = ? AND password = ?", (username, password))
        user = cursor.fetchone()
        
        connection.close()
        
        # Check if a user was found with the given credentials
        if user:
            session['username'] = username  # Store username in session
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password. Please try again.")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():   
    session.pop('username', None)  # Remove the username from session
    
    return redirect(url_for('home'))  # Redirect to login page
#Model predtion module
@app.route('/run-prediction', methods=['POST'])
def run_prediction():
    if request.method == 'POST':
        # Render the template when the button is clicked
        import matplotlib
        import matplotlib.pyplot as plt

        # Use non-interactive backend (for compatibility)
        matplotlib.use('Agg')

        # Load DHT11 sensor data (replace with your CSV file)
        data = pd.read_csv('sensor_data.csv')  # Example file with Temperature and Humidity

        # Selecting the relevant columns (Temperature and Humidity)
        sensor_data = data[['Temperature', 'Humidity']].values

        # Data normalization (scaling between 0 and 1)
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(sensor_data)

        # Create sequences for RNN
        def create_sequences(data, time_step=5):
            X, y = [], []
            for i in range(len(data) - time_step - 1):
                X.append(data[i:(i + time_step), :])  # Past readings
                y.append(data[i + time_step, :])      # Next reading to predict
            return np.array(X), np.array(y)

        # Sequence length (time step)
        time_step = 5
        X, y = create_sequences(scaled_data, time_step)

        # Split into training and testing sets (80% train, 20% test)
        train_size = int(len(X) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        # Define the RNN model
        model = Sequential()
        model.add(SimpleRNN(100, input_shape=(time_step, 2), return_sequences=False))  # RNN layer
        model.add(Dense(50, activation='relu'))  # Dense layer with 50 units
        model.add(Dense(2))  # Output layer for predicting 2 values (Temperature, Humidity)

        # Compile the model
        model.compile(optimizer='adam', loss='mean_squared_error')

        # Train the model
        history = model.fit(X_train, y_train, validation_data=(X_test, y_test), epochs=20, batch_size=32)

        # Make predictions on test data
        predictions = model.predict(X_test)

        # Inverse transform predictions to get original scale
        predicted_values = scaler.inverse_transform(predictions)
        actual_values = scaler.inverse_transform(y_test)

        # Plot actual vs predicted for Temperature
        plt.figure(figsize=(10, 5))
        plt.plot(actual_values[:, 0], label='Actual Temperature')
        plt.plot(predicted_values[:, 0], label='Predicted Temperature')
        plt.title('Temperature Prediction')
        plt.xlabel('Time Steps')
        plt.ylabel('Temperature')
        plt.legend()
        plt.savefig('/Users/charankurukuntla/ad_test/static/images/temperature_prediction.png')  # Save the plot to a file (avoid GUI issues)

        # Plot actual vs predicted for Humidity
        plt.figure(figsize=(10, 5))
        plt.plot(actual_values[:, 1], label='Actual Humidity')
        plt.plot(predicted_values[:, 1], label='Predicted Humidity')
        plt.title('Humidity Prediction')
        plt.xlabel('Time Steps')
        plt.ylabel('Humidity')
        plt.legend()
        plt.savefig('/Users/charankurukuntla/ad_test/static/images/humidity_prediction.png')  # Save the plot to a file (avoid GUI issues)

        return render_template('pred_result.html', n1=actual_values, n2=predicted_values)
    return render_template('index.html')

# data collection module
@app.route('/collect-data', methods=['POST'])
def collect_sensor_data():
    global collecting_data
    collecting_data = True
    
    try:
        ser = serial.Serial(arduino_port, baud_rate)
        time.sleep(2)  # Allow serial connection to initialize
        for _ in range(5):  # Discard initial garbled lines
            ser.readline()

        with open(output_file, mode='w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['Timestamp', 'Temperature', 'Humidity'])
            try:
                while collecting_data:
                    try:
                        raw_line = ser.readline()
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                    except Exception as e:
                        print(f"Error reading from serial: {e}")
                        continue

                    if line:
                        data = line.split(',')
                        if len(data) == 3:
                            timestamp, temperature, humidity = data
                            csv_writer.writerow([timestamp, temperature, humidity])
                            print(f"Timestamp: {timestamp}, Temperature: {temperature}°C, Humidity: {humidity}%")

                        else:
                            print(f"Invalid data received: {line}")
                    
            except KeyboardInterrupt:
                print("Stopped recording.")
            finally:
                ser.close()
        
    except serial.SerialException as e:
        return render_template('collecting.html', error_message=e)
    return render_template('collecting.html')
@app.route('/collect-data-error')
def collect_data_error():
    return render_template('collecting.html')

# stop collecting data function
@app.route('/stop-collection', methods=['POST'])
def stop_collecting_data():
    global collecting_data
    collecting_data = False
    return render_template('index.html')
#data showing function
@app.route('/show-data')
def show_data():
    with open(output_file, 'r') as csv_file:
        data = csv_file.readlines()
    return render_template('show_data.html', data=data)

#back button from show data to home page
@app.route('/back-button' , methods=['POST'])
def back_button():
    return render_template('index.html')

#data delete function
@app.route('/clear-data', methods=['POST'])
def clear_data():
    # Clear the contents of the CSV file
    with open(output_file, mode='w', newline='') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['Timestamp', 'Temperature', 'Humidity'])  # Write the header
    return render_template('index.html')


#Signp module

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=8080)
