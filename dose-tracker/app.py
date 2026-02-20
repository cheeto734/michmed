from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__, template_folder='.', static_folder='.')

DATA_FILE = 'patient_data.json'

def load_existing_data():
    """Load existing patient data from JSON file"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return []

def save_patient_data(data):
    """Append new patient data to JSON file"""
    patients = load_existing_data()
    patients.append(data)
    with open(DATA_FILE, 'w') as f:
        json.dump(patients, f, indent=2)

@app.route('/')
def index():
    """Serve the HTML template"""
    return render_template('template.html')

@app.route('/save-patient-data', methods=['POST'])
def save_data():
    """Handle form submission and save to JSON"""
    try:
        data = request.get_json()
        save_patient_data(data)
        return jsonify({'status': 'success', 'message': 'Patient data saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)