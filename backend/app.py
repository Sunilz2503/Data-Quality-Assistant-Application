import os
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
from data_context import DataContext
from ai_engine import AIEngine
from compliance_engine import ComplianceEngine
from rule_engine import RuleEngine
from dashboard_service import DashboardService
from utils import allowed_file, extract_text_from_pdf

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Global data context (production: use database)
data_context = DataContext()

@app.route('/upload-data', methods=['POST'])
def upload_data():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process file based on type
        if filename.endswith('.pdf'):
            data = extract_text_from_pdf(file_path)
        elif filename.endswith('.json'):
            data = pd.read_json(file_path)
        else:  # CSV
            data = pd.read_csv(file_path)
            
        data_context.update_dataset(data)
        return jsonify({"message": "File uploaded successfully"})
    
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/upload-policy', methods=['POST'])
def upload_policy():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file and allowed_file(file.filename) and file.filename.endswith('.pdf'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        policy_text = extract_text_from_pdf(file_path)
        data_context.update_policy(policy_text)
        return jsonify({"message": "Policy uploaded successfully"})
    
    return jsonify({"error": "Invalid file type. Only PDF accepted"}), 400

@app.route('/analyze-data', methods=['POST'])
def analyze_data():
    ai_engine = AIEngine(data_context)
    ai_engine.identify_cdes()
    ai_engine.recommend_rules()
    
    compliance_engine = ComplianceEngine(data_context)
    compliance_scores = compliance_engine.check_compliance()
    
    return jsonify({
        "cdes": data_context.cdes,
        "recommended_rules": data_context.recommended_rules,
        "compliance_scores": compliance_scores
    })

@app.route('/define-rules', methods=['POST'])
def define_rules():
    rules = request.json.get('rules', [])
    data_context.update_rules(rules)
    return jsonify({"message": "Rules updated successfully"})

@app.route('/run-quality-check', methods=['GET'])
def run_quality_check():
    rule_engine = RuleEngine(data_context)
    rule_engine.run_checks()
    return jsonify({
        "quality_scores": data_context.scores,
        "issues": data_context.issues
    })

@app.route('/dashboard', methods=['GET'])
def get_dashboard():
    dashboard = DashboardService(data_context)
    return jsonify(dashboard.get_dashboard_data())

@app.route('/export-report', methods=['GET'])
def export_report():
    # Generate JSON report
    report = {
        "data_summary": data_context.get_data_summary(),
        "cdes": data_context.cdes,
        "rules": data_context.rules,
        "quality_scores": data_context.scores,
        "compliance_scores": data_context.compliance_scores,
        "issues": data_context.issues
    }
    
    # Save to file
    report_path = os.path.join(app.config['UPLOAD_FOLDER'], 'dq_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f)
        
    return send_file(report_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)