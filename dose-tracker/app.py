from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os
import sqlite3
from datetime import datetime
import equations

app = Flask(__name__, template_folder='.', static_folder='static', static_url_path='/static')
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key')

DATA_FILE = 'patient_data.json'
TABLE_FILE = 'patient_table.json'
DB_FILE = 'dose_tracker.db'
SCHEMA_FILE = os.path.join('sql', 'schema.sql')
DRUG_FILE = 'drug_list.json'


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
        
def save_data_json_list(data, filename):
    json_file = load_existing_data(filename)
    json_file.append(data)
    with open(filename, 'w') as f:
        json.dump(json_file, f, indent=2)

def save_data_json_dict(key, value, filename):
    json_file = load_existing_data(filename)

    json_file[key] = value

    with open(filename, "w") as f:
        json.dump(json_file, f, indent=2)

def load_latest_schedule(reg_num):
    if not os.path.exists(TABLE_FILE):
        return []

    try:
        with open(TABLE_FILE, 'r') as f:
            saved_data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(saved_data, list):
        for entry in reversed(saved_data):
            if not isinstance(entry, dict):
                continue
            if str(entry.get('regNum')) != str(reg_num):
                continue
            doses = entry.get('doses', [])
            if isinstance(doses, list):
                return doses

    if isinstance(saved_data, dict) and str(saved_data.get('regNum')) == str(reg_num):
        doses = saved_data.get('doses', [])
        if isinstance(doses, list):
            return doses

    return []


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

@app.route('/patient_table/<user_url_slug>', methods=['GET'])
def patient_table_page(user_url_slug):
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    data = load_existing_data(DATA_FILE)
    
    with open("drug_list.json") as f:
        drug_list = json.load(f)
        
    for record in data:
        if int(record['registrationNumber']) == int(user_url_slug):
            height = float(record["height"])
            weight = float(record["weight"])
            sex = record["sex"]
            
            bsa = equations.BSA(height, weight)
            ibw = equations.IBW(height, sex)
            adj_bw = equations.adj_BW(weight, ibw)
            adj_bsa = equations.adj_BSA(height, weight)
            
            record["bsa"] = bsa
            record["ibw"] = ibw
            record["adj_bw"] = adj_bw
            record["adj_bsa"] = adj_bsa
            record["saved_schedule_rows"] = load_latest_schedule(record["registrationNumber"])
            
            return render_template('patient_table.html', **record, drug_list=drug_list)
        
    return redirect(url_for('patients_page'))

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

        save_data_json_list(data, DATA_FILE)
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
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

        data = request.get_json()

        reg_num = data.get('regNum')
        doses = data.get('doses')

        if reg_num is None or not isinstance(doses, list):
            return jsonify({'status': 'error', 'message': 'Missing schedule data'}), 400

        submission_data = {
            'submissionTime': datetime.now().isoformat(),
            'regNum': reg_num,
            'doses': doses
        }

        existing_data = load_existing_data(TABLE_FILE)
        if not isinstance(existing_data, list):
            existing_data = []

        updated = False
        for idx, entry in enumerate(existing_data):
            if isinstance(entry, dict) and str(entry.get('regNum')) == str(reg_num):
                existing_data[idx] = submission_data
                updated = True
                break

        if not updated:
            existing_data.append(submission_data)

        with open(TABLE_FILE, 'w') as f:
            json.dump(existing_data, f, indent=2)

        return jsonify({'status': 'success', 'message': 'Table data saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500   

@app.route('/update_drug_list', methods=['POST'])
def update_drugs():
    try:
        if 'user_id' not in session:
            return jsonify({'status': 'error', 'message': 'Not authenticated'}), 401

        data = request.get_json()
        print(data)

        new_drug_name = data['new_name']
        new_drug_doses = data['new_doses']
        new_drug_amount = data['new_amount']
        new_drug_interval = data['new_interval']
        
        print(new_drug_name)

        #todo
        save_data_json_dict(new_drug_name,
                            {"doses": new_drug_doses,
                             "intervalHours": new_drug_interval,
                             "amount": new_drug_amount},
                             DRUG_FILE)
        

        return jsonify({'status': 'success', 'message': 'New drug saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500   
           
if __name__ == '__main__':
    init_db()
    app.run(debug=True)