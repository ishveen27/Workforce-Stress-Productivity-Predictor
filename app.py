from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import pickle
import numpy as np

app = Flask(__name__)
app.secret_key = 'mental_health_secret'

# Load trained model
model = pickle.load(open('model/stress_model.pkl', 'rb'))

# SQLite connection
def get_db_connection():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    if 'user' in session:
        return redirect('/dashboard')
    return render_template('login_signup.html')

@app.route('/signup', methods=['POST'])
def signup():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return "Username already exists. Please choose a different one."

    cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session['user'] = username
        return redirect('/dashboard')
    return "Login Failed. Check your username and password."

@app.route('/dashboard')
def dashboard():
    if 'user' in session:
        return render_template('dashboard.html', user=session['user'])
    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        data = [
            float(request.form['work_stress']),
            float(request.form['emotional_state']),
            float(request.form['social_life']),
            float(request.form['sleep_hours'])
        ]
        prediction = model.predict([np.array(data)])
        stress = int(prediction[0])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO reports (username, stress_level) VALUES (?, ?)', (session['user'], stress))
        conn.commit()
        conn.close()

        selected_concerns = request.form.getlist('concerns')

        suggestion_dict = {
            "anxiety": "Try deep breathing exercises or mindfulness meditation.",
            "sleep": "Maintain a regular sleep schedule and reduce screen time before bed.",
            "work": "Practice time management and take short breaks during work.",
            "social": "Reach out to friends or join a support group.",
            "emotion": "Track your mood daily and express yourself through journaling.",
            "concentration": "Use focus techniques like Pomodoro or reduce distractions."
        }

        suggestions = [suggestion_dict[c] for c in selected_concerns if c in suggestion_dict]

        return render_template('result.html', stress=stress, suggestions=suggestions)

    return render_template('report.html')

@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT stress_level, submitted_at FROM reports WHERE username = ? ORDER BY submitted_at', (session['user'],))
    data = cursor.fetchall()
    conn.close()

    stress_levels = [row[0] for row in data]
    dates = [row[1] for row in data]

    return render_template('history.html', stress_levels=stress_levels, dates=dates)

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        comment = request.form['comment']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO feedback (username, comment) VALUES (?, ?)', (session['user'], comment))
        conn.commit()
        conn.close()
        return redirect('/dashboard')

    return render_template('feedback.html')

if __name__ == '__main__':
    app.run(debug=True)
