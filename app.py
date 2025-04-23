from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.database import Database
from bson import ObjectId
import os
from datetime import datetime, timedelta
import random
import string
import re
from typing import Any, Optional, cast
import certifi
from functools import wraps
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
import certifi


load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')

#Mongodb config
# MongoDB configuration
MONGODB_USERNAME = os.environ.get('MONGODB_USERNAME', 'your_username')
MONGODB_PASSWORD = os.environ.get('MONGODB_PASSWORD', 'your_password')
MONGODB_CLUSTER = os.environ.get('MONGODB_CLUSTER', 'your_cluster.mongodb.net')
MONGODB_DATABASE = os.environ.get('MONGODB_DATABASE', 'quizapp')

# MongoDB connection string
MONGODB_URI = f"mongodb+srv://{MONGODB_USERNAME}:{MONGODB_PASSWORD}@{MONGODB_CLUSTER}/?retryWrites=true&w=majority"

# MongoDB setup with SSL
client: Optional[MongoClient] = None
db: Optional[Database] = None

def connect_db() -> None:
    global client, db
    try:
        print(f"Attempting to connect to MongoDB with URI: mongodb+srv://{MONGODB_USERNAME}:****@{MONGODB_CLUSTER}/?retryWrites=true&w=majority")
        # Create a new client and connect to the server with SSL configuration
        client = MongoClient(
            MONGODB_URI,
            tls=True,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )
        
        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
        
        # Get database
        db = cast(Database, client[MONGODB_DATABASE])
        print(f"Connected to database: {MONGODB_DATABASE}")
        
    except Exception as e:
        print(f"MongoDB connection error: {str(e)}")
        print(f"MongoDB URI: mongodb+srv://{MONGODB_USERNAME}:****@{MONGODB_CLUSTER}/?retryWrites=true&w=majority")
        if client:
            client.close()
        client = None
        db = None
        raise

# Initialize connection
connect_db()

# Initialize the database
def init_db() -> None:
    if db is not None:
        db.users.drop()
        db.quizzes.drop()
        db.attempts.drop()


# Khởi tạo Firebase Admin SDK
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)
firestore_client = firestore.client()

# Configure session cookie settings
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Helper functions for MongoDB operations
def create_user(email: str, username: str, password: str, role: str) -> dict:
    user = {
        "email": email,
        "username": username,
        "password": password,
        "role": role,
        "created_at": datetime.utcnow()
    }
    result = db.users.insert_one(user)
    user["_id"] = result.inserted_id
    return user

def get_user_by_email(email: str) -> Optional[dict]:
    return db.users.find_one({"email": email})

def get_user_by_id(user_id: str) -> Optional[dict]:
    return db.users.find_one({"_id": ObjectId(user_id)})

def create_quiz(title: str, teacher_id: str, start_time: datetime, end_time: datetime, 
                duration: int, max_attempts: Optional[int], is_public: bool) -> dict:
    quiz = {
        "title": title,
        "quiz_code": generate_quiz_code(),
        "teacher_id": ObjectId(teacher_id),
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "max_attempts": max_attempts,
        "is_public": is_public,
        "questions": [],
        "created_at": datetime.utcnow()
    }
    result = db.quizzes.insert_one(quiz)
    quiz["_id"] = result.inserted_id
    return quiz

def get_quiz_by_id(quiz_id: str) -> Optional[dict]:
    return db.quizzes.find_one({"_id": ObjectId(quiz_id)})

def get_quiz_by_code(quiz_code: str) -> Optional[dict]:
    return db.quizzes.find_one({"quiz_code": quiz_code})

def create_question(quiz_id: str, question_text: str, question_type: str, 
                   correct_answer: str, answers: list = None) -> dict:
    question = {
        "quiz_id": ObjectId(quiz_id),
        "question_text": question_text,
        "question_type": question_type,
        "correct_answer": correct_answer,
        "answers": answers or [],
        "created_at": datetime.utcnow()
    }
    result = db.questions.insert_one(question)
    question["_id"] = result.inserted_id
    return question

def create_quiz_result(quiz_id: str, student_id: str, score: float) -> dict:
    result = {
        "quiz_id": ObjectId(quiz_id),
        "student_id": ObjectId(student_id),
        "score": score,
        "submitted_at": datetime.utcnow()
    }
    result_id = db.quiz_results.insert_one(result)
    result["_id"] = result_id.inserted_id
    return result

def create_student_answer(quiz_id: str, student_id: str, question_id: str, answer_text: str) -> dict:
    answer = {
        "quiz_id": ObjectId(quiz_id),
        "student_id": ObjectId(student_id),
        "question_id": ObjectId(question_id),
        "answer_text": answer_text,
        "submitted_at": datetime.utcnow()
    }
    result = db.student_answers.insert_one(answer)
    answer["_id"] = result.inserted_id
    return answer

def generate_quiz_code() -> str:
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if not get_quiz_by_code(code):
            return code

def create_user_profile(user_id: str, full_name: str = None) -> dict:
    profile = {
        "user_id": ObjectId(user_id),
        "full_name": full_name,
        "phone": None,
        "address": None,
        "bio": None,
        "avatar": None,
        "created_at": datetime.utcnow()
    }
    result = db.user_profiles.insert_one(profile)
    profile["_id"] = result.inserted_id
    return profile

def create_password_reset_token(user_id: str) -> dict:
    token = {
        "user_id": ObjectId(user_id),
        "token": ''.join(random.choices(string.ascii_letters + string.digits, k=32)),
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(hours=1),
        "used": False
    }
    result = db.password_reset_tokens.insert_one(token)
    token["_id"] = result.inserted_id
    return token

# Routes
@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = get_user_by_email(email)
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            session['username'] = user['username']
            flash('Đăng nhập thành công!', "success")
            
            if user['role'] == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            else:
                return redirect(url_for('home'))
        
        flash('Email hoặc mật khẩu không đúng!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            role = request.form['role']

            # Kiểm tra username và email đã tồn tại
            existing_user = db.users.find_one({
                "$or": [
                    {"username": username},
                    {"email": email}
                ]
            })
            
            if existing_user:
                if existing_user['email'] == email:
                    flash('Email đã được sử dụng. Vui lòng dùng email khác!', 'error')
                else:
                    flash('Tên đăng nhập đã tồn tại. Vui lòng chọn tên đăng nhập khác!', 'error')
                return redirect(url_for('register'))

            # Mã hóa mật khẩu
            hashed_password = generate_password_hash(password)
            
            # Tạo user mới
            new_user = create_user(email, username, hashed_password, role)
            
            # Tạo profile cho user
            create_user_profile(str(new_user['_id']), username)

            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            flash('Có lỗi xảy ra. Vui lòng thử lại!', 'error')
            return redirect(url_for('register'))

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
    
    teacher_id = session['user_id']
    
    # Lấy tổng số bài kiểm tra của giáo viên
    total_quizzes = db.quizzes.count_documents({"teacher_id": ObjectId(teacher_id)})
    
    # Lấy số lượng học sinh đã tham gia các bài kiểm tra
    quiz_ids = [q["_id"] for q in db.quizzes.find({"teacher_id": ObjectId(teacher_id)}, {"_id": 1})]
    total_students = len(db.quiz_results.distinct("student_id", {"quiz_id": {"$in": quiz_ids}}))
    
    # Lấy 5 bài kiểm tra gần đây nhất
    recent_quizzes = list(db.quizzes.find(
        {"teacher_id": ObjectId(teacher_id)}
    ).sort("created_at", -1).limit(5))
    
    return render_template('teacher_dashboard.html',
                         total_quizzes=total_quizzes,
                         total_students=total_students,
                         recent_quizzes=recent_quizzes)

@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    if not user or user['role'] != 'teacher':
        flash('Chỉ giáo viên mới có thể tạo bài kiểm tra')
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # Tạo bài kiểm tra mới
            title = request.form['title']
            start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            duration = int(request.form['duration'])
            max_attempts = request.form.get('max_attempts')
            is_public = request.form.get('is_public') == 'on'
            
            quiz = create_quiz(
                title=title,
                teacher_id=session['user_id'],
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                max_attempts=int(max_attempts) if max_attempts else None,
                is_public=is_public
            )
            
            # Lấy dữ liệu từ form
            questions = request.form.getlist('questions[]')
            question_types = request.form.getlist('question_types[]')
            correct_answers = request.form.getlist('correct_answers[]')
            
            # Thêm câu hỏi và câu trả lời
            for i in range(len(questions)):
                answers = []
                if question_types[i] == 'multiple_choice':
                    for j in range(4):
                        option = request.form.getlist(f'option{j+1}[]')[i]
                        if option:
                            answers.append({"text": option})
                
                create_question(
                    quiz_id=str(quiz['_id']),
                    question_text=questions[i],
                    question_type=question_types[i],
                    correct_answer=correct_answers[i],
                    answers=answers
                )
            
            flash(f'Tạo bài kiểm tra thành công! Mã bài kiểm tra: {quiz["quiz_code"]}')
            return redirect(url_for('manage_quizzes'))
            
        except Exception as e:
            flash(f'Có lỗi xảy ra khi tạo bài kiểm tra: {str(e)}')
            return redirect(url_for('create_quiz'))
    
    return render_template('create_quiz.html')

@app.route('/teacher/manage-quizzes')
def manage_quizzes():
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy danh sách bài kiểm tra của giáo viên từ database
    teacher_id = session['user_id']
    quizzes = list(db.quizzes.find({"teacher_id": ObjectId(teacher_id)}))
    
    return render_template('manage_quizzes.html', quizzes=quizzes)

# Lịch sử bài kiểm tra
@app.route('/history')
def history():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem lịch sử!')
        return redirect(url_for('login'))
    
    if session['role'] == 'student':
        results = list(db.quiz_results.find({"student_id": ObjectId(session['user_id'])}).sort("submitted_at", -1))
        return render_template('history.html', results=results, datetime=datetime)
    else:
        quizzes = list(db.quizzes.find())
        return render_template('history.html', quizzes=quizzes, datetime=datetime)

@app.route('/view-quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    quiz = get_quiz_by_id(quiz_id)
    user = get_user_by_id(session['user_id'])
    
    # Kiểm tra quyền truy cập
    if user.role != 'teacher' or quiz['teacher_id'] != user['_id']:
        flash('Bạn không có quyền truy cập bài kiểm tra này!')
        return redirect(url_for('home'))
    
    # Lấy danh sách câu hỏi của bài kiểm tra
    questions = list(db.questions.find({"quiz_id": ObjectId(quiz_id)}))
    
    return render_template('view_quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = get_quiz_by_id(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz['teacher_id'] != ObjectId(session['user_id']):
        flash('Bạn không có quyền chỉnh sửa bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    if request.method == 'POST':
        try:
            # Cập nhật thông tin cơ bản của bài kiểm tra
            update_data = {
                "title": request.form.get('title'),
                "start_time": datetime.fromisoformat(request.form.get('start_time').replace('Z', '+00:00')),
                "end_time": datetime.fromisoformat(request.form.get('end_time').replace('Z', '+00:00')),
                "duration": int(request.form.get('duration')),
                "max_attempts": int(request.form.get('max_attempts')) if request.form.get('max_attempts') else None,
                "is_public": request.form.get('is_public') == 'on'
            }
            
            db.quizzes.update_one({"_id": ObjectId(quiz_id)}, {"$set": update_data})
            
            # Lấy dữ liệu từ form
            questions = request.form.getlist('questions[]')
            question_types = request.form.getlist('question_types[]')
            correct_answers = request.form.getlist('correct_answers[]')
            
            # Xóa câu hỏi và câu trả lời cũ
            db.questions.delete_many({"quiz_id": ObjectId(quiz_id)})
            db.answers.delete_many({"question_id": {"$in": [ObjectId(q['_id']) for q in db.questions.find({"quiz_id": ObjectId(quiz_id)})]}})
            
            # Thêm câu hỏi mới
            for i in range(len(questions)):
                question = {
                    "quiz_id": ObjectId(quiz_id),
                    "question_text": questions[i],
                    "question_type": question_types[i],
                    "correct_answer": correct_answers[i],
                    "answers": [],
                    "created_at": datetime.utcnow()
                }
                result = db.questions.insert_one(question)
                question["_id"] = result.inserted_id
                
                # Nếu là câu hỏi trắc nghiệm, thêm các lựa chọn
                if question_types[i] == 'multiple_choice':
                    for j in range(4):
                        option = request.form.getlist(f'option{j+1}[]')[i]
                        if option:  # Chỉ thêm option nếu có giá trị
                            answer = {
                                "question_id": question["_id"],
                                "answer_text": option
                            }
                            db.answers.insert_one(answer)
            
            flash('Cập nhật bài kiểm tra thành công!', 'success')
            return redirect(url_for('manage_quizzes'))
            
        except Exception as e:
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
    quiz = get_quiz_by_id(quiz_id)
    
    # Kiểm tra xem người dùng có phải là chủ sở hữu của bài kiểm tra không
    if quiz['teacher_id'] != ObjectId(session['user_id']):
        flash('Bạn không có quyền xóa bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    try:
        # Xóa các kết quả bài kiểm tra trước
        db.quiz_results.delete_many({"quiz_id": ObjectId(quiz_id)})
        
        # Lấy danh sách câu hỏi của bài kiểm tra
        questions = list(db.questions.find({"quiz_id": ObjectId(quiz_id)}))
        
        # Xóa các câu trả lời và câu hỏi
        for question in questions:
            db.answers.delete_many({"question_id": question['_id']})
        
        db.questions.delete_many({"quiz_id": ObjectId(quiz_id)})
        
        # Xóa bài kiểm tra
        db.quizzes.delete_one({"_id": ObjectId(quiz_id)})
        flash('Xóa bài kiểm tra thành công!')
    except Exception as e:
        flash(f'Có lỗi xảy ra khi xóa bài kiểm tra: {str(e)}')
    
    return redirect(url_for('manage_quizzes'))

@app.route('/search')
def search_quiz():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return redirect(url_for('home'))
    
    # Tìm kiếm tất cả bài kiểm tra
    quizzes = list(db.quizzes.find({"title": {"$regex": f"{keyword}", "$options": "i"}}))
    
    return render_template('search_results.html', 
                         quizzes=quizzes, 
                         keyword=keyword)

@app.route('/join_quiz', methods=['GET', 'POST'])
def join_quiz():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để tham gia bài kiểm tra!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        quiz_code = request.form.get('quiz_code')
        quiz = get_quiz_by_code(quiz_code)

        if not quiz:
            flash('Mã bài kiểm tra không tồn tại!', 'error')
            return redirect(url_for('join_quiz'))

        # Kiểm tra thời gian
        current_time = datetime.now()  # Sử dụng datetime.now() thay vì utcnow()
        if current_time < quiz['start_time']:
            flash('Bài kiểm tra chưa bắt đầu!', 'error')
            return redirect(url_for('join_quiz'))
        
        if current_time > quiz['end_time']:
            flash('Bài kiểm tra đã kết thúc!', 'error')
            return redirect(url_for('join_quiz'))

        # Kiểm tra số lần làm bài
        if quiz['max_attempts']:
            attempt_count = db.quiz_results.count_documents({
                "quiz_id": ObjectId(quiz['_id']),
                "student_id": ObjectId(session['user_id'])
            })
            
            if attempt_count >= quiz['max_attempts']:
                flash(f'Bạn đã vượt quá số lần làm bài cho phép ({quiz["max_attempts"]} lần)!', 'error')
                return redirect(url_for('join_quiz'))

        # Chuyển hướng đến trang làm bài với mã bài kiểm tra
        return redirect(url_for('take_quiz', quiz_id=quiz['_id'], quiz_code=quiz['quiz_code']))

    return render_template('join_quiz.html')

@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để làm bài kiểm tra!', 'error')
        return redirect(url_for('login'))

    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash('Không tìm thấy bài kiểm tra!', 'error')
        return redirect(url_for('home'))
    
    # Kiểm tra quyền truy cập
    if session['role'] == 'student':
        if not quiz['is_public']:
            # Nếu là bài kiểm tra riêng tư, kiểm tra mã
            quiz_code = request.args.get('quiz_code')
            if not quiz_code or quiz_code != quiz['quiz_code']:
                flash('Bài kiểm tra này ở chế độ riêng tư. Vui lòng sử dụng mã bài kiểm tra để tham gia!', 'error')
                return redirect(url_for('join_quiz'))

    # Kiểm tra thời gian
    current_time = datetime.now()
    if current_time < quiz['start_time']:
        flash('Bài kiểm tra chưa bắt đầu!', 'error')
        return redirect(url_for('home'))
    
    if current_time > quiz['end_time']:
        flash('Bài kiểm tra đã kết thúc!', 'error')
        return redirect(url_for('home'))

    # Kiểm tra số lần làm bài
    if quiz['max_attempts']:
        attempt_count = db.quiz_results.count_documents({
            "quiz_id": ObjectId(quiz_id),
            "student_id": ObjectId(session['user_id'])
        })
        
        if attempt_count >= quiz['max_attempts']:
            flash(f'Bạn đã vượt quá số lần làm bài cho phép ({quiz["max_attempts"]} lần)!', 'error')
            return redirect(url_for('home'))

    # Lấy danh sách câu hỏi của bài kiểm tra
    questions = list(db.questions.find({"quiz_id": ObjectId(quiz_id)}))
    
    return render_template('take_quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz/submit/<quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Bạn không có quyền thực hiện hành động này!')
        return redirect(url_for('home'))
    
    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash('Không tìm thấy bài kiểm tra!')
        return redirect(url_for('home'))
    
    # Kiểm tra thời gian
    now = datetime.now()
    if now > quiz['end_time']:
        flash('Bài kiểm tra đã kết thúc!')
        return redirect(url_for('home'))
    
    # Lấy câu trả lời từ form
    score = 0
    questions = list(db.questions.find({"quiz_id": ObjectId(quiz_id)}))
    total_questions = len(questions)
    
    for question in questions:
        answer = request.form.get(f'answer_{question["_id"]}')
        
        # Lưu câu trả lời vào database
        create_student_answer(
            quiz_id=quiz_id,
            student_id=session['user_id'],
            question_id=str(question['_id']),
            answer_text=answer or ""
        )
        
        # Kiểm tra đáp án
        if question['question_type'] == 'multiple_choice':
            if answer:
                selected_answer = db.answers.find_one({"_id": ObjectId(answer)})
                if selected_answer and selected_answer['text'].strip() == question['correct_answer'].strip():
                    score += 1
        else:  # fill_in_blank
            if answer and answer.strip().lower() == question['correct_answer'].strip().lower():
                score += 1
    
    # Tính điểm theo thang 10
    final_score = (score / total_questions) * 10 if total_questions > 0 else 0
    
    # Lưu kết quả vào database
    create_quiz_result(quiz_id, session['user_id'], final_score)

    return redirect(url_for('results_page', quiz_id=quiz_id))

@app.route('/results/<quiz_id>')
def results_page(quiz_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để xem kết quả!')
        return redirect(url_for('login'))

    quiz = get_quiz_by_id(quiz_id)
    if not quiz:
        flash('Không tìm thấy bài kiểm tra!')
        return redirect(url_for('home'))

    # Lấy kết quả của user
    result = db.quiz_results.find_one({
        "quiz_id": ObjectId(quiz_id),
        "student_id": ObjectId(session['user_id'])
    }, sort=[("submitted_at", -1)])
    
    if not result:
        flash('Không tìm thấy kết quả bài kiểm tra của bạn.')
        return redirect(url_for('home'))

    # Lấy danh sách câu hỏi
    questions = list(db.questions.find({"quiz_id": ObjectId(quiz_id)}))

    # Lấy câu trả lời của học sinh
    student_answers = list(db.student_answers.find({
        "quiz_id": ObjectId(quiz_id),
        "student_id": ObjectId(session['user_id'])
    }))
    
    # Chuyển đổi dữ liệu thành dictionary {question_id: answer_text}
    student_answers_dict = {}
    for answer in student_answers:
        question = db.questions.find_one({"_id": answer['question_id']})
        if question:  # Kiểm tra xem câu hỏi có tồn tại không
            if question['question_type'] == 'multiple_choice':
                # Lấy text của câu trả lời từ bảng Answer
                selected_answer = db.answers.find_one({"_id": ObjectId(answer['answer_text'])})
                student_answers_dict[str(answer['question_id'])] = selected_answer['text'] if selected_answer else "Chưa trả lời"
            else:
                # Với câu điền vào chỗ trống, lấy trực tiếp answer_text
                student_answers_dict[str(answer['question_id'])] = answer['answer_text']

    # Chuẩn bị dữ liệu cho template    
    results = []
    for question in questions:
        user_answer = student_answers_dict.get(str(question['_id']), "Chưa trả lời")
        is_correct = False
        
        if question['question_type'] == 'multiple_choice':
            is_correct = user_answer.strip() == question['correct_answer'].strip() if user_answer != "Chưa trả lời" else False
        else:  # fill_in_blank
            is_correct = user_answer.strip().lower() == question['correct_answer'].strip().lower() if user_answer != "Chưa trả lời" else False
            
        results.append((question['question_text'], user_answer, question['correct_answer'], is_correct, question['question_type']))

    return render_template(
        'results_after.html', 
        quiz=quiz, 
        score=result['score'], 
        total_questions=len(questions),
        results=results
    )


@app.route('/quiz/<int:quiz_id>/results')
def quiz_results(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    # Lấy thông tin bài kiểm tra
    quiz = get_quiz_by_id(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz['teacher_id'] != ObjectId(session['user_id']):
        flash('Bạn không có quyền xem kết quả bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Lấy danh sách kết quả của học sinh
    results = list(db.quiz_results.find({"quiz_id": ObjectId(quiz_id)}).sort("score", -1))
    
    return render_template('quiz_results.html', quiz=quiz, results=results)

@app.route('/quiz/<int:quiz_id>/students')
def quiz_students(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    quiz = get_quiz_by_id(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz['teacher_id'] != ObjectId(session['user_id']):
        flash('Bạn không có quyền xem kết quả bài kiểm tra này!')
        return redirect(url_for('history'))
    
    # Lấy danh sách kết quả của học sinh
    results = list(db.quiz_results.find({"quiz_id": ObjectId(quiz_id)}).sort("score", -1))
    
    return render_template('quiz_students.html', quiz=quiz, results=results)

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    if not user:
        flash('Không tìm thấy thông tin người dùng!')
        return redirect(url_for('home'))
        
    user_profile = db.user_profiles.find_one({"user_id": ObjectId(session['user_id'])})
    
    if not user_profile:
        user_profile = create_user_profile(session['user_id'])
    
    return render_template('profile.html', user=user, profile=user_profile)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    if not user:
        flash('Không tìm thấy thông tin người dùng!')
        return redirect(url_for('home'))
        
    profile = db.user_profiles.find_one({"user_id": ObjectId(session['user_id'])})
    
    if request.method == 'POST':
        # Cập nhật thông tin profile
        update_data = {
            "full_name": request.form.get('full_name'),
            "phone": request.form.get('phone'),
            "address": request.form.get('address'),
            "bio": request.form.get('bio')
        }
        
        db.user_profiles.update_one(
            {"user_id": ObjectId(session['user_id'])},
            {"$set": update_data}
        )
        
        flash('Cập nhật thông tin thành công!')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=user, profile=profile)

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    if not user:
        flash('Không tìm thấy thông tin người dùng!')
        return redirect(url_for('home'))
        
    return render_template('settings.html', user=user)

@app.route('/settings/password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = get_user_by_id(session['user_id'])
    if not user:
        flash('Không tìm thấy thông tin người dùng!')
        return redirect(url_for('home'))
        
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not check_password_hash(user['password'], current_password):
        flash('Mật khẩu hiện tại không đúng!')
        return redirect(url_for('settings'))
    
    if new_password != confirm_password:
        flash('Mật khẩu mới không khớp!')
        return redirect(url_for('settings'))
    
    # Cập nhật mật khẩu mới
    db.users.update_one(
        {"_id": ObjectId(session['user_id'])},
        {"$set": {"password": generate_password_hash(new_password)}}
    )
    
    flash('Đổi mật khẩu thành công!')
    return redirect(url_for('settings'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = get_user_by_email(email)
        
        if user:
            # Tạo token reset mật khẩu
            reset_token = create_password_reset_token(str(user['_id']))
            
            # Redirect trực tiếp đến trang reset password
            return redirect(url_for('reset_password', token=reset_token['token']))
        
        flash('Email không tồn tại trong hệ thống.', 'error')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = db.password_reset_tokens.find_one({
        "token": token,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    if not reset_token:
        flash('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp.', 'error')
            return render_template('reset_password.html')
        
        # Cập nhật mật khẩu mới cho user
        db.users.update_one(
            {"_id": reset_token['user_id']},
            {"$set": {"password": generate_password_hash(password)}}
        )
        
        # Đánh dấu token đã sử dụng
        db.password_reset_tokens.update_one(
            {"_id": reset_token['_id']},
            {"$set": {"used": True}}
        )
        
        flash('Mật khẩu đã được đặt lại thành công. Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/quiz/<int:quiz_id>/toggle-visibility')
def toggle_quiz_visibility(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền thực hiện hành động này!')
        return redirect(url_for('home'))
    
    quiz = get_quiz_by_id(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz['teacher_id'] != ObjectId(session['user_id']):
        flash('Bạn không có quyền thay đổi trạng thái bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Đảo ngược trạng thái công khai
    db.quizzes.update_one({"_id": ObjectId(quiz_id)}, {"$set": {"is_public": not quiz['is_public']}})
    
    status = "công khai" if not quiz['is_public'] else "riêng tư"
    flash(f'Trạng thái bài kiểm tra đã được thay đổi thành {status}!')
    return redirect(url_for('manage_quizzes'))

@app.route('/login/google')
def login_google():
    return render_template('login_google.html')

@app.route('/login/google/callback', methods=['POST'])
def google_callback():
    try:
        if 'firebase_admin' not in globals() or firestore_client is None:
            return jsonify({'success': False, 'error': 'Firebase chưa được khởi tạo'}), 500
            
        # Lấy token ID từ request
        id_token = request.json.get('idToken')
        
        if not id_token:
            return jsonify({'success': False, 'error': 'Không tìm thấy token'}), 400
            
        # Xác thực token với Firebase
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', email.split('@')[0])
        
        # Kiểm tra xem người dùng đã tồn tại chưa
        user = get_user_by_email(email)
        if not user:
            # Tạo người dùng mới
            hashed_password = generate_password_hash(str(random.getrandbits(128)))  # Tạo mật khẩu ngẫu nhiên
            user = create_user(email, name, hashed_password, 'student')  # Mặc định là student
            
            # Tạo profile cho người dùng mới
            create_user_profile(str(user['_id']), name)

        # Đăng nhập người dùng
        session['user_id'] = str(user['_id'])
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'redirect': url_for('home')})
        
    except Exception as e:
        print(f"Error in google_callback: {str(e)}")  # Log lỗi
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/register/google/callback', methods=['POST'])
def register_google_callback():
    try:
        if 'firebase_admin' not in globals() or firestore_client is None:
            return jsonify({'success': False, 'error': 'Firebase chưa được khởi tạo'}), 500
            
        data = request.get_json()
        id_token = data.get('idToken')
        role = data.get('role')

        if not id_token or not role:
            return jsonify({'success': False, 'error': 'Thiếu thông tin cần thiết'}), 400

        # Xác thực token với Firebase
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token['email']
        name = decoded_token.get('name', email.split('@')[0])

        # Kiểm tra xem email đã tồn tại chưa
        existing_user = get_user_by_email(email)
        if existing_user:
            return jsonify({'success': False, 'error': 'Email đã được sử dụng'}), 400

        # Tạo username từ email nếu không có name
        username = name
        # Nếu username đã tồn tại, thêm số ngẫu nhiên
        while db.users.find_one({"username": username}):
            username = f"{name}{random.randint(1000, 9999)}"

        # Tạo mật khẩu ngẫu nhiên cho tài khoản
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))

        # Tạo user mới
        new_user = create_user(
            email=email,
            username=username,
            password=generate_password_hash(password),
            role=role
        )

        # Tạo profile cho user
        create_user_profile(
            user_id=str(new_user['_id']),
            full_name=name
        )

        # Đăng nhập người dùng
        session['user_id'] = str(new_user['_id'])
        session['username'] = new_user['username']
        session['role'] = new_user['role']

        # Chuyển hướng dựa trên role
        redirect_url = url_for('teacher_dashboard') if role == 'teacher' else url_for('home')

        return jsonify({
            'success': True,
            'redirect': redirect_url
        })

    except auth.InvalidIdTokenError:
        return jsonify({'success': False, 'error': 'Token không hợp lệ'}), 401
    except auth.ExpiredIdTokenError:
        return jsonify({'success': False, 'error': 'Token đã hết hạn'}), 401
    except auth.RevokedIdTokenError:
        return jsonify({'success': False, 'error': 'Token đã bị thu hồi'}), 401
    except Exception as e:
        print(f"Error in register_google_callback: {str(e)}")
        return jsonify({'success': False, 'error': 'Có lỗi xảy ra khi đăng ký'}), 500

def main():
    try:
        port = int(os.environ.get('PORT', 8080))
        print(f"Starting server on port {port}")
        app.run(host='0.0.0.0', port=8080)
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        raise


if __name__ == "__main__":
    main()