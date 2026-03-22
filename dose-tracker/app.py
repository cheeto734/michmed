from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime
import equations

app = Flask(__name__, template_folder='.', static_folder='.')

DATA_FILE = 'patient_data.json'
TABLE_FILE = 'patient_table.json'

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
        
@app.route('/')
def index():
    """Serve the HTML template"""
    return render_template('template.html')

@app.route('/save-patient-data', methods=['POST'])
def save_data():
    """Handle form submission and save to JSON"""
    try:
        data = request.get_json()
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
        
        # Handle array of dosage rows
        if isinstance(data, list):
            submission_data = {
                'submissionTime': datetime.now().isoformat(),
                'doses': data
            }
        else:
            # Handle single object for backwards compatibility
            submission_data = data
        
        save_data_json(submission_data, TABLE_FILE)
        return jsonify({'status': 'success', 'message': 'Table data saved'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500   
        
if __name__ == '__main__':
    app.run(debug=True)