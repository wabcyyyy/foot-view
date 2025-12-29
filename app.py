from flask import Flask, request, jsonify, render_template, redirect, url_for
import os
import pandas as pd
from backend.processing import process_video
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///footview.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 确保上传和输出文件夹存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- Models ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    records = db.relationship('AnalysisRecord', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class AnalysisRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 可以添加更多字段，如总分、等级等

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Auth Routes ---
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'})

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'})

    new_user = User(username=username)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'success': True, 'message': '注册成功'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({'success': True, 'message': '登录成功', 'user': {'username': user.username}})
    
    return jsonify({'success': False, 'message': '用户名或密码错误'})

@app.route('/api/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'success': True, 'message': '已注销'})

@app.route('/api/user/current')
def get_current_user():
    if current_user.is_authenticated:
        return jsonify({'is_authenticated': True, 'user': {'username': current_user.username}})
    else:
        return jsonify({'is_authenticated': False})

# --- Main Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'video' not in request.files:
        return jsonify({'success': False, 'message': '没有提供视频文件'})
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'})
    
    if file:
        # 使用时间戳防止文件名冲突
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # 记录到数据库
        record = AnalysisRecord(filename=filename, user=current_user)
        db.session.add(record)
        db.session.commit()

        process_video(filename, filepath, app.config['OUTPUT_FOLDER'])
        
        return jsonify({'success': True, 'filename': filename})

@app.route('/api/analysis/<filename>')
@login_required
def api_analysis(filename):
    # 检查该文件是否属于当前用户
    record = AnalysisRecord.query.filter_by(filename=filename, user_id=current_user.id).first()
    if not record:
        return jsonify({'success': False, 'message': '无权访问或记录不存在'})

    video_base_name = os.path.splitext(filename)[0]
    analysis_file = os.path.join(app.config['OUTPUT_FOLDER'], video_base_name, f"{video_base_name}_analysis.csv")
    
    if os.path.exists(analysis_file):
        df = pd.read_csv(analysis_file, encoding='utf-8-sig')
        analysis_data = df.to_dict('records')
        
        fall_warning = ""
        with open(analysis_file, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
            for line in lines:
                if '警告：' in line:
                    fall_warning = line.strip()
                    break
        
        return jsonify({'success': True, 'data': analysis_data, 'fall_warning': fall_warning})
    else:
        return jsonify({'success': False, 'message': '分析结果未找到'})

@app.route('/api/history')
@login_required
def history():
    records = AnalysisRecord.query.filter_by(user_id=current_user.id).order_by(AnalysisRecord.upload_date.desc()).all()
    history_data = [{
        'id': r.id,
        'filename': r.filename,
        'upload_date': r.upload_date.strftime('%Y-%m-%d %H:%M:%S')
    } for r in records]
    return jsonify({'success': True, 'data': history_data})

# 初始化数据库
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
