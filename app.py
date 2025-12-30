from flask import Flask, request, jsonify, render_template, redirect, url_for, send_from_directory
import os
import random
import string
import numpy as np
import pandas as pd
from backend.processing import process_video, set_fall_alert_callback
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_mail import Mail, Message

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///footview.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ========== 邮箱配置 - 请修改以下配置 ==========
app.config['MAIL_SERVER'] = 'smtp.qq.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = '2592438525@qq.com'  # TODO: 改为您的QQ邮箱
app.config['MAIL_PASSWORD'] = 'eetxmjziimckdhhd'  # TODO: 改为您的QQ邮箱授权码（16位）
app.config['MAIL_DEFAULT_SENDER'] = ('FootView', '2592438525@qq.com')  # TODO: 改为您的QQ邮箱
# =============================================

mail = Mail(app)

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
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    records = db.relationship('AnalysisRecord', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class VerificationCode(db.Model):
    """邮箱验证码存储"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    def is_valid(self):
        """检查验证码是否有效"""
        return not self.used and datetime.utcnow() < self.expires_at

class AnalysisRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # 可以添加更多字段，如总分、等级等

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- 验证码相关函数 ---
def generate_verification_code():
    """生成6位数字验证码"""
    return ''.join(random.choices(string.digits, k=6))


def send_verification_email(email, code):
    """发送验证码邮件"""
    try:
        msg = Message(
            subject='【FootView】邮箱验证码',
            recipients=[email],
            body=f'''您好！

您正在注册 FootView 账号，您的验证码是：

{code}

验证码有效期为 10 分钟，请尽快完成验证。

如果这不是您本人的操作，请忽略此邮件。

FootView 团队
'''
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"发送邮件失败: {e}")
        return False


def send_fall_alert_email(email, filename, fall_times, fall_warning):
    """
    发送摔倒警报邮件
    
    Args:
        email: 用户邮箱
        filename: 视频文件名
        fall_times: 摔倒发生时间列表
        fall_warning: 警告信息
    
    Returns:
        bool: 发送是否成功
    """
    try:
        # 格式化摔倒时间
        fall_times_str = ', '.join([f"{t:.2f}秒" for t in fall_times]) if fall_times else "未知"
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        msg = Message(
            subject='⚠️【FootView 紧急警报】检测到摔倒事件！',
            recipients=[email],
            body=f'''⚠️ 紧急警报 ⚠️

FootView 步态分析系统检测到摔倒事件！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📹 视频文件: {filename}

⏰ 检测时间: {current_time}

🔴 摔倒发生时间点: {fall_times_str}

📊 检测结果: {fall_warning}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请及时查看视频分析结果，确认情况并采取必要措施。

如有紧急情况，请立即联系相关人员。

此邮件由 FootView 系统自动发送，请勿直接回复。

FootView 团队
'''
        )
        mail.send(msg)
        print(f"摔倒警报邮件发送成功: {email}")
        return True
    except Exception as e:
        print(f"发送摔倒警报邮件失败: {e}")
        return False


# 注册摔倒警报回调函数
set_fall_alert_callback(send_fall_alert_email)


# --- Auth Routes ---
@app.route('/api/send-verification-code', methods=['POST'])
def send_verification_code():
    """发送邮箱验证码"""
    data = request.get_json()
    email = data.get('email', '').strip()

    if not email:
        return jsonify({'success': False, 'message': '请输入邮箱地址'})

    # 简单的邮箱格式验证
    if '@' not in email or '.' not in email:
        return jsonify({'success': False, 'message': '邮箱格式不正确'})

    # 检查邮箱是否已被注册
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '该邮箱已被注册'})

    # 检查是否频繁发送（60秒内只能发送一次）
    recent_code = VerificationCode.query.filter_by(email=email).order_by(
        VerificationCode.created_at.desc()
    ).first()
    if recent_code and (datetime.utcnow() - recent_code.created_at).total_seconds() < 60:
        return jsonify({'success': False, 'message': '发送太频繁，请稍后再试'})

    # 生成验证码
    code = generate_verification_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)

    # 保存验证码
    verification = VerificationCode(email=email, code=code, expires_at=expires_at)
    db.session.add(verification)
    db.session.commit()

    # 发送邮件
    if send_verification_email(email, code):
        return jsonify({'success': True, 'message': '验证码已发送，请查收邮件'})
    else:
        return jsonify({'success': False, 'message': '发送失败，请检查邮箱地址或稍后重试'})


@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password')
    verification_code = data.get('verification_code', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'})

    if not email:
        return jsonify({'success': False, 'message': '邮箱不能为空'})

    if not verification_code:
        return jsonify({'success': False, 'message': '请输入验证码'})

    # 检查用户名是否存在
    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'})

    # 检查邮箱是否已被注册
    if User.query.filter_by(email=email).first():
        return jsonify({'success': False, 'message': '该邮箱已被注册'})

    # 验证验证码
    verification = VerificationCode.query.filter_by(
        email=email, code=verification_code, used=False
    ).order_by(VerificationCode.created_at.desc()).first()

    if not verification:
        return jsonify({'success': False, 'message': '验证码错误'})

    if not verification.is_valid():
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'})

    # 标记验证码已使用
    verification.used = True

    # 创建用户
    new_user = User(username=username, email=email)
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

        # 处理视频，传入用户邮箱用于摔倒警报通知
        process_video(filename, filepath, app.config['OUTPUT_FOLDER'], 
                     user_email=current_user.email)
        
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
        # 删除空行（指标列为空的行）
        if '指标' in df.columns:
            df = df.dropna(subset=['指标'], how='all')
            df = df[df['指标'].astype(str).str.strip() != '']
        elif '参数' in df.columns:
            # 兼容旧格式
            df = df.dropna(subset=['参数'], how='all')
            df = df[df['参数'].astype(str).str.strip() != '']
        # 将 NaN 替换为空字符串，避免 JSON 序列化问题
        df = df.fillna('')
        analysis_data = df.to_dict('records')
        
        # 读取摔倒警告信息
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


@app.route('/api/history/<int:record_id>', methods=['DELETE'])
@login_required
def delete_record(record_id):
    """
    删除历史分析记录
    
    同时删除：
    1. 数据库记录
    2. 上传的视频文件
    3. 输出文件夹（分析结果、骨架视频等）
    """
    import shutil
    
    # 查找记录，确保属于当前用户
    record = AnalysisRecord.query.filter_by(id=record_id, user_id=current_user.id).first()
    
    if not record:
        return jsonify({'success': False, 'message': '记录不存在或无权删除'}), 404
    
    filename = record.filename
    video_base_name = os.path.splitext(filename)[0]
    
    try:
        # 1. 删除上传的视频文件
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(upload_path):
            os.remove(upload_path)
        
        # 2. 删除输出文件夹
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], video_base_name)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        
        # 3. 删除数据库记录
        db.session.delete(record)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '记录已删除'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


def filter_outliers(values, hard_limits=None, use_iqr=True):
    """
    过滤异常值
    
    使用两种策略：
    1. 硬边界过滤：超出物理合理范围的值
    2. IQR 统计过滤：使用四分位距法过滤统计异常值
    
    Args:
        values: 数值列表
        hard_limits: 硬边界 [min, max]，None 表示不限制
        use_iqr: 是否使用 IQR 方法过滤
    
    Returns:
        过滤后的数值列表，被过滤的异常值数量
    """
    if not values:
        return [], 0
    
    filtered = list(values)
    outlier_count = 0
    
    # 1. 硬边界过滤
    if hard_limits:
        hard_min, hard_max = hard_limits
        before_count = len(filtered)
        filtered = [v for v in filtered if hard_min <= v <= hard_max]
        outlier_count += before_count - len(filtered)
    
    # 2. IQR 统计过滤（至少需要4个数据点）
    if use_iqr and len(filtered) >= 4:
        q1 = np.percentile(filtered, 25)
        q3 = np.percentile(filtered, 75)
        iqr = q3 - q1
        
        # 使用 1.5 * IQR 作为异常值边界
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        before_count = len(filtered)
        filtered = [v for v in filtered if lower_bound <= v <= upper_bound]
        outlier_count += before_count - len(filtered)
    
    return filtered, outlier_count


def calculate_dynamic_range(values, base_range, metric_type='normal', hard_limits=None):
    """
    计算动态健康区间（带异常值过滤）
    
    算法：
    1. 先过滤异常值
    2. 如果有效数据 < 5 次，使用放宽的基准范围
    3. 如果有效数据 >= 5 次，计算个人参考区间：
       - 个人均值 ± 1.5 * 标准差
       - 与基准范围取加权融合（70% 个人数据 + 30% 基准）
    
    Args:
        values: 历史数值列表
        base_range: 基准范围 [min, max]
        metric_type: 指标类型
        hard_limits: 硬边界限制（用于过滤异常值）
    
    Returns:
        动态范围 [min, max], 过滤的异常值数量
    """
    # 过滤异常值
    valid_values, outlier_count = filter_outliers(values, hard_limits, use_iqr=True)
    
    if not valid_values:
        valid_values = [v for v in values if v is not None]
    
    if len(valid_values) < 5:
        # 数据不足，使用基准范围
        return base_range, outlier_count
    
    mean = np.mean(valid_values)
    std = np.std(valid_values)
    
    # 防止标准差过小
    min_std = abs(mean) * 0.1 if mean != 0 else 1.0
    std = max(std, min_std)
    
    # 个人参考区间：均值 ± 1.5 * 标准差
    personal_min = mean - 1.5 * std
    personal_max = mean + 1.5 * std
    
    # 根据指标类型调整
    if metric_type == 'lower_better':
        # 越小越好的指标，下限可以放宽到0
        personal_min = max(0, personal_min)
    
    # 与基准范围加权融合（70% 个人 + 30% 基准）
    weight_personal = 0.7
    weight_base = 0.3
    
    final_min = weight_personal * personal_min + weight_base * base_range[0]
    final_max = weight_personal * personal_max + weight_base * base_range[1]
    
    # 确保范围合理
    if metric_type == 'lower_better':
        final_min = max(0, final_min)
    
    return [round(final_min, 2), round(final_max, 2)], outlier_count


@app.route('/api/history/metrics')
@login_required
def history_metrics():
    """
    获取用户的历史分析指标数据（用于仪表盘图表）
    返回最近的分析记录及其指标数据
    
    特性：
    - 为中老年人放宽的基准范围
    - 基于历史数据的动态个人健康区间
    """
    records = AnalysisRecord.query.filter_by(user_id=current_user.id).order_by(AnalysisRecord.upload_date.asc()).all()
    
    # 指标定义（为中老年人放宽的基准范围）
    # base_range: 放宽后的基准范围
    # hard_limits: 物理意义上的合理边界（用于过滤检测错误导致的极端值）
    # type: 指标类型（用于动态区间计算）
    metrics_config = {
        '步频': {
            'unit': '步/分', 
            'description': '每分钟步数', 
            'base_range': [70, 130],
            'hard_limits': [30, 200],  # 物理上不可能低于30或高于200
            'type': 'normal'
        },
        '步态周期': {
            'unit': '秒', 
            'description': '单步时间', 
            'base_range': [0.6, 1.6],
            'hard_limits': [0.3, 3.0],  # 单步不可能少于0.3秒或超过3秒
            'type': 'normal'
        },
        '对称性指数': {
            'unit': '%', 
            'description': '越小越对称', 
            'base_range': [0, 10],
            'hard_limits': [0, 50],  # 超过50%的不对称属于检测错误
            'type': 'lower_better'
        },
        '变异系数': {
            'unit': '%', 
            'description': '越小越稳定', 
            'base_range': [0, 50],  # 放宽：中老年人变异系数普遍较高
            'hard_limits': [0, 120],  # 放宽硬边界，只过滤极端异常值
            'type': 'lower_better'
        },
        '躯干稳定性': {
            'unit': '度/帧', 
            'description': '越小越稳定', 
            'base_range': [0, 1.0],
            'hard_limits': [0, 5.0],  # 超过5度/帧属于检测错误
            'type': 'lower_better'
        },
        '膝关节活动度': {
            'unit': '度', 
            'description': '膝关节屈伸范围', 
            'base_range': [30, 80],
            'hard_limits': [5, 120],  # 膝关节活动度应在5-120度之间
            'type': 'normal'
        },
    }
    
    history_data = []
    # 收集每个指标的所有历史值（用于计算动态区间）
    all_metric_values = {name: [] for name in metrics_config}
    
    for record in records:
        video_base_name = os.path.splitext(record.filename)[0]
        analysis_file = os.path.join(app.config['OUTPUT_FOLDER'], video_base_name, f"{video_base_name}_analysis.csv")
        
        if os.path.exists(analysis_file):
            try:
                df = pd.read_csv(analysis_file, encoding='utf-8-sig')
                
                # 解析指标数据
                metrics = {}
                for _, row in df.iterrows():
                    name = row.get('指标') or row.get('参数')
                    value = row.get('数值') if '数值' in df.columns else row.get('测量值')
                    
                    if name and name in metrics_config:
                        # 尝试转换为数字（处理 pandas NaN 和空值）
                        try:
                            # 检查是否为空值（包括 pandas NaN）
                            if pd.isna(value) or value == '' or value == '无':
                                metrics[name] = None
                            else:
                                val = float(value)
                                metrics[name] = val
                                all_metric_values[name].append(val)
                        except (ValueError, TypeError):
                            metrics[name] = None
                
                history_data.append({
                    'id': record.id,
                    'filename': record.filename,
                    'date': record.upload_date.strftime('%m-%d'),
                    'full_date': record.upload_date.strftime('%Y-%m-%d %H:%M'),
                    'metrics': metrics
                })
            except Exception as e:
                print(f"读取分析文件失败: {e}")
                continue
    
    # 计算每个指标的动态区间（带异常值过滤）
    for name, config in metrics_config.items():
        base_range = config['base_range']
        metric_type = config.get('type', 'normal')
        hard_limits = config.get('hard_limits')
        values = all_metric_values[name]
        
        # 计算动态区间（返回范围和异常值数量）
        dynamic_range, outlier_count = calculate_dynamic_range(
            values, base_range, metric_type, hard_limits
        )
        config['normal_range'] = dynamic_range
        
        # 过滤后的有效值（用于统计）
        filtered_values, _ = filter_outliers(values, hard_limits, use_iqr=True)
        if not filtered_values:
            filtered_values = [v for v in values if v is not None]
        
        # 添加数据统计信息
        if filtered_values:
            config['stats'] = {
                'count': len(filtered_values),
                'total_count': len([v for v in values if v is not None]),
                'outliers_filtered': outlier_count,
                'mean': round(float(np.mean(filtered_values)), 2),
                'std': round(float(np.std(filtered_values)), 2),
                'min': round(float(min(filtered_values)), 2),
                'max': round(float(max(filtered_values)), 2)
            }
        else:
            config['stats'] = None
    
    return jsonify({
        'success': True, 
        'data': history_data,
        'metrics_config': metrics_config
    })


@app.route('/api/video/<filename>')
@login_required
def get_video(filename):
    """
    获取骨架检测视频文件
    
    Args:
        filename: 原始视频文件名（带扩展名）
    
    Returns:
        视频文件流
    """
    # 检查该文件是否属于当前用户
    record = AnalysisRecord.query.filter_by(filename=filename, user_id=current_user.id).first()
    if not record:
        return jsonify({'success': False, 'message': '无权访问或记录不存在'}), 403

    video_base_name = os.path.splitext(filename)[0]
    video_folder = os.path.join(app.config['OUTPUT_FOLDER'], video_base_name)
    skeleton_video = f"{video_base_name}_skeleton.mp4"
    
    video_path = os.path.join(video_folder, skeleton_video)
    if os.path.exists(video_path):
        # 使用绝对路径
        abs_folder = os.path.abspath(video_folder)
        return send_from_directory(
            abs_folder, 
            skeleton_video, 
            mimetype='video/mp4'
        )
    else:
        return jsonify({'success': False, 'message': '视频文件未找到'}), 404

# 初始化数据库
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
