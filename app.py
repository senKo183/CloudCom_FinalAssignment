from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mathquiz.db'
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    questions = db.relationship('Question', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.String(500), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice' or other types
    correct_answer = db.Column(db.String(500), nullable=False)
    answers = db.relationship('Answer', backref='question', lazy=True)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.String(500), nullable=False)

def init_db():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")

# Routes
@app.route('/')
@app.route('/home')  # Thêm route này
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash('Đăng nhập thành công!')
            
            # Chuyển hướng dựa trên role
            if user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('home'))
        
        flash('Email hoặc mật khẩu không đúng!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')

        if password != confirm_password:
            flash('Mật khẩu không khớp!')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email đã tồn tại!')
            return render_template('register.html')

        user = User(
            email=email,
            username=username,
            password=generate_password_hash(password),
            role=role
        )
        db.session.add(user)
        db.session.commit()
        flash('Đăng ký thành công!')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Thêm route mặc định để xử lý 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin thực tế từ database
    teacher_id = session['user_id']
    
    # Lấy tổng số bài kiểm tra của giáo viên
    total_quizzes = Quiz.query.filter_by(teacher_id=teacher_id).count()
    
    # Lấy số lượng học sinh đã tham gia các bài kiểm tra (sẽ cập nhật sau khi có bảng Student_Quiz)
    total_students = 0
    
    # Lấy 5 bài kiểm tra gần đây nhất
    recent_quizzes = Quiz.query.filter_by(teacher_id=teacher_id).order_by(Quiz.id.desc()).limit(5).all()
    
    return render_template('teacher_dashboard.html',
                         total_quizzes=total_quizzes,
                         total_students=total_students,
                         recent_quizzes=recent_quizzes)

@app.route('/create-quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        start_time = datetime.fromisoformat(request.form.get('start_time').replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(request.form.get('end_time').replace('Z', '+00:00'))
        duration = int(request.form.get('duration'))
        questions = request.form.getlist('questions[]')
        question_types = request.form.getlist('question_types[]')
        correct_answers = request.form.getlist('correct_answers[]')
        
        # Tạo bài kiểm tra mới
        quiz = Quiz(
            title=title,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            teacher_id=session['user_id']
        )
        db.session.add(quiz)
        db.session.commit()
        
        # Thêm các câu hỏi
        for i in range(len(questions)):
            question = Question(
                quiz_id=quiz.id,
                question_text=questions[i],
                question_type=question_types[i],
                correct_answer=correct_answers[i]
            )
            db.session.add(question)
            db.session.commit()  # Commit question to get its ID
            
            # Nếu là câu hỏi trắc nghiệm, thêm các lựa chọn
            if question_types[i] == 'multiple_choice':
                for j in range(4):
                    option = request.form.getlist(f'option{j+1}[]')[i]
                    answer = Answer(
                        question_id=question.id,  # Now question.id exists
                        answer_text=option
                    )
                    db.session.add(answer)
        
        db.session.commit()
        flash('Tạo bài kiểm tra thành công!')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_quiz.html')

@app.route('/teacher/manage-quizzes')
def manage_quizzes():
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy danh sách bài kiểm tra của giáo viên từ database
    teacher_id = session['user_id']
    quizzes = Quiz.query.filter_by(teacher_id=teacher_id).order_by(Quiz.id.desc()).all()
    
    return render_template('manage_quizzes.html', quizzes=quizzes)

# Lịch sử bài kiểm tra
@app.route('/history')
def history():
    # Lấy danh sách bài kiểm tra đã hoàn thành từ database
    user_id = session.get('id')  # Lấy ID người dùng từ session
    quizzes = Quiz.query.filter_by(id=user_id).order_by(Quiz.start_time.desc()).all()  # Lọc các bài kiểm tra của người dùng
    
    return render_template('history.html', quizzes=quizzes)

def main():
    with app.app_context():
        # Chỉ tạo bảng nếu chưa tồn tại
        db.create_all()
    app.run(debug=True)

if __name__ == "__main__":
    main() 