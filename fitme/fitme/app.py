import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import google.generativeai as genai
from datetime import datetime
import json
import plotly
import plotly.express as px
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a secure secret key

# Configure Google Gemini API
GOOGLE_API_KEY = 'your_gemini_api_key_here'  # Replace with your actual API key
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# Database configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345678',
    'database': 'fitme_db'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table with additional fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(80) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(100),
            weight FLOAT,
            height FLOAT,
            age INT,
            gender VARCHAR(20),
            activity_level VARCHAR(50),
            plan_type VARCHAR(50),
            tracking_period INT
        )
    ''')
    
    # Create progress tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            date DATE NOT NULL,
            exercise_name VARCHAR(255) NOT NULL,
            is_completed BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create meal tracking table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meal_tracking (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            date DATE NOT NULL,
            meal_type VARCHAR(50) NOT NULL,
            meal_description TEXT NOT NULL,
            is_completed BOOLEAN DEFAULT FALSE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # Create chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

# Initialize database
init_db()

@app.route('/')
def index():
    return render_template('first.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password')
        
        cursor.close()
        conn.close()
        
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        weight = request.form.get('weight')
        height = request.form.get('height')
        age = request.form.get('age')
        gender = request.form.get('gender')
        activity_level = request.form.get('activity_level')
        plan_type = request.form.get('plan_type')
        tracking_period = request.form.get('tracking_period')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if username exists
        cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
        if cursor.fetchone():
            flash('Username already exists')
            cursor.close()
            conn.close()
            return redirect(url_for('register'))
        
        # Create new user with profile information
        password_hash = generate_password_hash(password)
        cursor.execute('''
            INSERT INTO users (
                username, password_hash, name, weight, height, 
                age, gender, activity_level, plan_type, tracking_period
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            username, password_hash, name, weight, height,
            age, gender, activity_level, plan_type, tracking_period
        ))
        conn.commit()
        
        flash('Registration successful! Please login.')
        cursor.close()
        conn.close()
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')

@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chatbot.html')

@app.route('/calendar')
def calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('calendar.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/get_exercise_recommendations', methods=['GET'])
def get_exercise_recommendations():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    # Generate exercise recommendations using Gemini API
    prompt = f"""
    Generate a daily exercise plan for a person with the following characteristics:
    - Age: {user['age']}
    - Gender: {user['gender']}
    - Activity Level: {user['activity_level']}
    - Plan Type: {user['plan_type']}
    
    Please provide 5 specific exercises with these details for each:
    1. Exercise name
    2. Duration/Reps
    3. Difficulty level
    4. Target muscle groups
    Format the response as a JSON array.
    """
    
    response = model.generate_content(prompt)
    exercises = json.loads(response.text)
    
    # Store exercises in progress tracking
    today = datetime.now().date()
    for exercise in exercises:
        cursor.execute('''
            INSERT INTO user_progress (user_id, date, exercise_name, is_completed)
            VALUES (%s, %s, %s, FALSE)
        ''', (session['user_id'], today, exercise['name']))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify(exercises)

@app.route('/get_meal_suggestions', methods=['GET'])
def get_meal_suggestions():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    # Generate meal suggestions using Gemini API
    prompt = f"""
    Generate a daily meal plan for a person with the following characteristics:
    - Age: {user['age']}
    - Gender: {user['gender']}
    - Activity Level: {user['activity_level']}
    
    Please provide meals for:
    1. Breakfast
    2. Lunch
    3. Dinner
    4. 2 Snacks
    
    Include calories and macronutrients for each meal.
    Format the response as a JSON array.
    """
    
    response = model.generate_content(prompt)
    meals = json.loads(response.text)
    
    # Store meals in meal tracking
    today = datetime.now().date()
    for meal in meals:
        cursor.execute('''
            INSERT INTO meal_tracking (user_id, date, meal_type, meal_description, is_completed)
            VALUES (%s, %s, %s, %s, FALSE)
        ''', (session['user_id'], today, meal['type'], json.dumps(meal)))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify(meals)

@app.route('/update_progress', methods=['POST'])
def update_progress():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    progress_id = request.json.get('progress_id')
    is_completed = request.json.get('is_completed')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE user_progress 
        SET is_completed = %s 
        WHERE id = %s AND user_id = %s
    ''', (is_completed, progress_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/update_meal', methods=['POST'])
def update_meal():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    meal_id = request.json.get('meal_id')
    is_completed = request.json.get('is_completed')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE meal_tracking 
        SET is_completed = %s 
        WHERE id = %s AND user_id = %s
    ''', (is_completed, meal_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/get_progress_graph', methods=['GET'])
def get_progress_graph():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get exercise completion data
    cursor.execute('''
        SELECT date, COUNT(*) as total, 
        SUM(CASE WHEN is_completed THEN 1 ELSE 0 END) as completed
        FROM user_progress 
        WHERE user_id = %s 
        GROUP BY date 
        ORDER BY date
    ''', (session['user_id'],))
    
    progress_data = cursor.fetchall()
    df = pd.DataFrame(progress_data)
    
    # Create progress graph
    fig = px.line(df, x='date', y=['total', 'completed'],
                  title='Your Fitness Progress',
                  labels={'value': 'Number of Exercises', 'date': 'Date'},
                  color_discrete_map={'total': 'gray', 'completed': 'green'})
    
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    cursor.close()
    conn.close()
    
    return jsonify(graphJSON)

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
        
    message = request.json.get('message')
    
    # Get user context
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
    user = cursor.fetchone()
    
    # Generate response using Gemini API
    prompt = f"""
    As a fitness assistant, please provide advice for a user with these characteristics:
    - Age: {user['age']}
    - Gender: {user['gender']}
    - Activity Level: {user['activity_level']}
    
    User Question: {message}
    
    Please provide a detailed and personalized response.
    """
    
    response = model.generate_content(prompt)
    
    # Store chat history
    cursor.execute('''
        INSERT INTO chat_history (user_id, message, response)
        VALUES (%s, %s, %s)
    ''', (session['user_id'], message, response.text))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({'response': response.text})

if __name__ == '__main__':
    app.run(debug=True) 