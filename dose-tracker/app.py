from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import sqlite3
from datetime import datetime
import equations

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

DATA_FILE = 'patient_data.json'
TABLE_FILE = 'patient_table.json'
DB_FILE = 'dose_tracker.db'
SCHEMA_FILE = os.path.join('sql', 'schema.sql')


def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if not os.path.exists(DB_FILE):
        with sqlite3.connect(DB_FILE) as conn:
            with open(SCHEMA_FILE, 'r') as schema_file:
                conn.executescript(schema_file.read())
            # Seed a default user for quick local testing.
            # conn.execute('INSERT INTO users (username) VALUES (?)', ('admin',))
            # user_id = conn.execute('SELECT user_id FROM users WHERE username = ?', ('admin',)).fetchone()[0]
            # conn.execute('INSERT INTO passwords (user_id, password) VALUES (?, ?)', (user_id, 'admin123'))
            conn.commit()

def load_existing_data(filename):
    """Load existing patient data from JSON file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []
        
def save_data_json(data, filename):
    json_file = load_existing_data(filename)
    json_file.append(data)
    with open(filename, 'w') as f:
        json.dump(json_file, f, indent=2)


@app.context_processor
def inject_username():
    return {'username': session.get('username')}
        
@app.route('/')
def index():
    """Default landing page"""
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return redirect(url_for('patients_page'))


@app.route('/add-patient', methods=['GET'])
def add_patient_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    return render_template('template.html')


@app.route('/login', methods=['GET'])
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/patients', methods=["GET"])
def patients_page():
    if 'user_id' not in session:
        return redirect(url_for('login_page'))

    with get_db_connection() as conn:
        patients = conn.execute(
            '''
            SELECT p.patient_id AS patient_id, p.firstName AS firstName, p.lastName AS lastName, p.regNum AS regNum
            FROM patients p
            WHERE p.user_id = ?
            ORDER BY p.timestamp DESC
            ''',
            (session['user_id'],)
        ).fetchall()

    return render_template('patients.html', patients=patients)

@app.route('/new-user', methods=['GET'])
def new_user_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template('new_user.html')


@app.route('/new-user', methods=['POST'])
def create_user():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('new_user.html', error='Username and password are required.')

        with get_db_connection() as conn:
            try:
                cursor = conn.execute('INSERT INTO users (username) VALUES (?)', (username,))
                user_id = cursor.lastrowid
                conn.execute('INSERT INTO passwords (user_id, password) VALUES (?, ?)', (user_id, password))
                conn.commit()
            except sqlite3.IntegrityError:
                return render_template('new_user.html', error='Username already exists.')

        return render_template('login.html', success='Account created. Please log in.')
    except Exception as e:
        return render_template('new_user.html', error=f'Unable to create user: {str(e)}')


@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            return render_template('login.html', error='Username and password are required.')

        with get_db_connection() as conn:
            user = conn.execute(
                '''
                SELECT u.user_id, u.username
                FROM users u
                JOIN passwords p ON p.user_id = u.user_id
                WHERE u.username = ? AND p.password = ?
                ''',
                (username, password)
            ).fetchone()

        if user is None:
            return render_template('login.html', error='Invalid username or password.')

        session['user_id'] = user['user_id']
        session['username'] = user['username']
        return redirect(url_for('patients_page'))
    except Exception as e:
        return render_template('login.html', error=f'Login failed: {str(e)}')


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/save-patient-data', methods=['POST'])
def save_data():
    """Handle form submission and save to JSON"""
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

        data = request.get_json()

        first_name = data.get('firstName', '').strip()
        last_name = data.get('lastName', '').strip()
        reg_num = data.get('registrationNumber')

        if not first_name or not last_name or reg_num is None:
            return jsonify({'status': 'error', 'message': 'Missing required patient fields'}), 400

        with get_db_connection() as conn:
            conn.execute(
                '''
                INSERT INTO patients (firstName, lastName, regNum, user_id)
                VALUES (?, ?, ?, ?)
                ''',
                (first_name, last_name, int(reg_num), session['user_id'])
            )
            conn.commit()

        save_data_json(data, DATA_FILE)
        return jsonify({'status': 'success', 'message': 'Patient data saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/calculate', methods=['POST'])
def calculate_metrics():
    """Handle metric calculations"""
    try:
        data = request.get_json()
        height = float(data["height"])
        weight = float(data["weight"])
        sex = data["sex"]
        
        bsa = equations.BSA(height, weight)
        ibw = equations.IBW(height, sex)
        adj_bw = equations.adj_BW(weight, ibw)
        adj_bsa = equations.adj_BSA(height, weight)
        
        return jsonify({
            "bsa": bsa,
            "ibw": ibw,
            "adj_bw": adj_bw,
            "adj_bsa": adj_bsa
        }), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500     
@app.route('/save-table-data', methods=['POST'])
def save_table():
    try:
        data = request.get_json()
        
        if isinstance(data, list):
            submission_data = {
                'submissionTime': datetime.now().isoformat(),
                'doses': data
            }
        else:
            submission_data = data
        
        save_data_json(submission_data, TABLE_FILE)
        return jsonify({'status': 'success', 'message': 'Table data saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500   
        
if __name__ == '__main__':
    init_db()
    app.run(debug=True)