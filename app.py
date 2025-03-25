from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mathquiz.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class User(db.Model):
    id = db.Column(db.Integer , primary_key=True)
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
    teacher = db.relationship('User', backref='quizzes', lazy=True)

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

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    quiz = db.relationship('Quiz', backref='results', lazy=True)
    student = db.relationship('User', backref='quiz_results', lazy=True)

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
            flash('Đăng nhập thành công!',"success")
            
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
    
    # Lấy số lượng học sinh đã tham gia các bài kiểm tra
    total_students = QuizResult.query.join(Quiz, QuizResult.quiz_id == Quiz.id)\
        .filter(Quiz.teacher_id == teacher_id)\
        .distinct(QuizResult.student_id)\
        .count()
    
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
                        question_id=question.id,
                        answer_text=option
                    )
                    db.session.add(answer)
            
            elif question_types[i] == 'fill_in_blank':
                # Câu hỏi điền vào chỗ trống chỉ cần lưu đáp án đúng
                pass
        
        db.session.commit()
        flash('Tạo bài kiểm tra thành công!')
        return redirect(url_for('teacher_dashboard'))
    
    return render_template('create_quiz_new.html')

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
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem lịch sử!')
        return redirect(url_for('login'))
    
    # Lấy lịch sử làm bài của học sinh
    if session['role'] == 'student':
        results = QuizResult.query\
            .filter_by(student_id=session['user_id'])\
            .order_by(QuizResult.submitted_at.desc())\
            .all()
        return render_template('history.html', results=results)
    
    # Lấy lịch sử bài kiểm tra của giáo viên
    elif session['role'] == 'teacher':
        quizzes = Quiz.query\
            .filter_by(teacher_id=session['user_id'])\
            .order_by(Quiz.start_time.desc())\
            .all()
        return render_template('history.html', quizzes=quizzes)
    
    return redirect(url_for('home'))

@app.route('/view-quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra xem người dùng có phải là chủ sở hữu của bài kiểm tra không
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền xem bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Lấy danh sách câu hỏi của bài kiểm tra
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    return render_template('view_quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền chỉnh sửa bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    if request.method == 'POST':
        try:
            # Cập nhật thông tin cơ bản của bài kiểm tra
            quiz.title = request.form.get('title')
            quiz.start_time = datetime.fromisoformat(request.form.get('start_time').replace('Z', '+00:00'))
            quiz.end_time = datetime.fromisoformat(request.form.get('end_time').replace('Z', '+00:00'))
            quiz.duration = int(request.form.get('duration'))
            
            # Lưu thay đổi thông tin cơ bản
            db.session.commit()
            
            # Lấy dữ liệu từ form
            questions = request.form.getlist('questions[]')
            question_types = request.form.getlist('question_types[]')
            correct_answers = request.form.getlist('correct_answers[]')
            
            # Xóa câu hỏi và câu trả lời cũ
            for old_question in quiz.questions:
                Answer.query.filter_by(question_id=old_question.id).delete()
            Question.query.filter_by(quiz_id=quiz.id).delete()
            db.session.commit()
            
            # Thêm câu hỏi mới
            for i in range(len(questions)):
                question = Question(
                    quiz_id=quiz.id,
                    question_text=questions[i],
                    question_type=question_types[i],
                    correct_answer=correct_answers[i]
                )
                db.session.add(question)
                db.session.flush()  # Để lấy được ID của câu hỏi mới
                
                # Nếu là câu hỏi trắc nghiệm, thêm các lựa chọn
                if question_types[i] == 'multiple_choice':
                    for j in range(4):
                        option = request.form.getlist(f'option{j+1}[]')[i]
                        if option:  # Chỉ thêm option nếu có giá trị
                            answer = Answer(
                                question_id=question.id,
                                answer_text=option
                            )
                            db.session.add(answer)
            
            # Lưu tất cả thay đổi
            db.session.commit()
            flash('Cập nhật bài kiểm tra thành công!', 'success')
            return redirect(url_for('manage_quizzes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra khi cập nhật bài kiểm tra: {str(e)}', 'error')
            return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    
    # GET request - hiển thị form chỉnh sửa
    return render_template('edit_quiz.html', quiz=quiz)

@app.route('/delete-quiz/<int:quiz_id>')
def delete_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra xem người dùng có phải là chủ sở hữu của bài kiểm tra không
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền xóa bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Lấy danh sách câu hỏi của bài kiểm tra
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    # Xóa các câu trả lời và câu hỏi
    for question in questions:
        Answer.query.filter_by(question_id=question.id).delete()
    
    Question.query.filter_by(quiz_id=quiz_id).delete()
    
    # Xóa bài kiểm tra
    db.session.delete(quiz)
    db.session.commit()
    
    flash('Xóa bài kiểm tra thành công!')
    return redirect(url_for('manage_quizzes'))

@app.route('/search')
def search_quiz():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return redirect(url_for('home'))
    
    # Tìm kiếm bài kiểm tra theo tiêu đề và join với bảng User để lấy thông tin giáo viên
    quizzes = Quiz.query.join(User, Quiz.teacher_id == User.id)\
                       .filter(Quiz.title.ilike(f'%{keyword}%'))\
                       .all()
    
    return render_template('search_results.html', 
                         quizzes=quizzes, 
                         keyword=keyword)

# Thêm route để tham gia bài kiểm tra (nếu chưa có)
@app.route('/join-quiz/<int:quiz_id>', methods=['POST'])
def join_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để tham gia bài kiểm tra!')
        return redirect(url_for('login'))
    
    if session['role'] != 'student':
        flash('Chỉ học sinh mới có thể tham gia bài kiểm tra!')
        return redirect(url_for('home'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra thời gian
    now = datetime.now()
    if now < quiz.start_time:
        flash('Bài kiểm tra chưa bắt đầu!')
        return redirect(url_for('home'))
    
    if now > quiz.end_time:
        flash('Bài kiểm tra đã kết thúc!')
        return redirect(url_for('home'))
    
    return redirect(url_for('take_quiz', quiz_id=quiz_id))

@app.route('/quiz/take/<int:quiz_id>')
def take_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để tham gia bài kiểm tra!')
        return redirect(url_for('login'))
    
    if session['role'] != 'student':
        flash('Chỉ học sinh mới có thể tham gia bài kiểm tra!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra thời gian
    now = datetime.now()
    if now < quiz.start_time:
        flash('Bài kiểm tra chưa bắt đầu!')
        return redirect(url_for('home'))
    
    if now > quiz.end_time:
        flash('Bài kiểm tra đã kết thúc!')
        return redirect(url_for('home'))
    
    # Lấy danh sách câu hỏi
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    return render_template('take_quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz/submit/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Bạn không có quyền thực hiện hành động này!')
        return redirect(url_for('home'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra thời gian
    now = datetime.now()
    if now > quiz.end_time:
        flash('Bài kiểm tra đã kết thúc!')
        return redirect(url_for('home'))
    
    # Lấy câu trả lời từ form
    answers = {}
    score = 0
    total_questions = len(quiz.questions)
    
    for question in quiz.questions:
        answer = request.form.get(f'answer_{question.id}')
        answers[question.id] = answer
        
        # Kiểm tra đáp án
        if question.question_type == 'multiple_choice':
            selected_answer = Answer.query.get(int(answer)) if answer else None
            if selected_answer and selected_answer.answer_text == question.correct_answer:
                score += 1
        else:  # fill_in_blank
            if answer and answer.strip().lower() == question.correct_answer.strip().lower():
                score += 1
    
    # Tính điểm theo thang 10
    final_score = (score / total_questions) * 10
    
    # Lưu kết quả vào database
    quiz_result = QuizResult(
        quiz_id=quiz_id,
        student_id=session['user_id'],
        score=final_score
    )
    db.session.add(quiz_result)
    db.session.commit()
    
    flash(f'Nộp bài thành công! Điểm của bạn: {final_score:.2f}/10')
    return redirect(url_for('home'))

@app.route('/quiz/<int:quiz_id>/results')
def quiz_results(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền xem kết quả bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Lấy danh sách kết quả của học sinh
    results = QuizResult.query.filter_by(quiz_id=quiz_id)\
        .join(User, QuizResult.student_id == User.id)\
        .order_by(QuizResult.score.desc())\
        .all()
    
    return render_template('quiz_results.html', quiz=quiz, results=results)

@app.route('/quiz/<int:quiz_id>/students')
def quiz_students(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền xem kết quả bài kiểm tra này!')
        return redirect(url_for('history'))
    
    # Lấy danh sách kết quả của học sinh
    results = QuizResult.query.filter_by(quiz_id=quiz_id)\
        .join(User, QuizResult.student_id == User.id)\
        .order_by(QuizResult.score.desc())\
        .all()
    
    return render_template('quiz_students.html', quiz=quiz, results=results)

def main():
    with app.app_context():
        # Chỉ tạo bảng nếu chưa tồn tại
        db.create_all()
    app.run(debug=True)


if __name__ == "__main__":
    main() 