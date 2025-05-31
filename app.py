from sqlalchemy.orm import joinedload
from markupsafe import Markup
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from flask_migrate import Migrate
from sqlalchemy.exc import IntegrityError
import random
import string
import re
from werkzeug.utils import secure_filename

# Import cho chatbot
from langchain_community.llms import CTransformers
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mathquiz.db'
# Cấu hình upload
UPLOAD_FOLDER = 'static/uploads/question_images'
CHATBOT_UPLOAD_FOLDER = 'data'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
PDF_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CHATBOT_UPLOAD_FOLDER'] = CHATBOT_UPLOAD_FOLDER

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
    quiz_code = db.Column(db.String(10), unique=True, nullable=True, server_default=None)  # Make it nullable with default None
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # in minutes
    max_attempts = db.Column(db.Integer, nullable=True, default=None)  # Số lần làm bài tối đa
    is_public = db.Column(db.Boolean, default=False)  # Thêm trường is_public
    questions = db.relationship('Question', backref='quiz', lazy='joined')
    teacher = db.relationship('User', backref='quizzes', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    #question_text = db.Column(db.String(500), nullable=False)
    question_text = db.Column(db.Text, nullable=False) #Đổi String thành Text để lưu LaTeX dài
    question_type = db.Column(db.String(20), nullable=False)  # 'multiple_choice' or other types
    #correct_answer = db.Column(db.String(500), nullable=False)
    correct_answer = db.Column(db.Text, nullable=False)  # Đổi String thành Text
    image_path = db.Column(db.String(255), nullable=False)  # Thêm đường dẫn hình ảnh
    answers = db.relationship('Answer', backref='question', lazy='joined')

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    #answer_text = db.Column(db.String(500), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    submitted_at = db.Column(db.DateTime, nullable=False, default=datetime.now)
    
    quiz = db.relationship('Quiz', backref='results', lazy=True)
    student = db.relationship('User', backref='quiz_results', lazy=True)

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.String(200))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='profile', lazy=True)

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref='reset_tokens', lazy=True)

class StudentAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    answer_text = db.Column(db.String(500), nullable=False)

    quiz = db.relationship('Quiz', backref='student_answers', lazy=True)
    student = db.relationship('User', backref='student_answers', lazy=True)
    question = db.relationship('Question', backref='student_answers', lazy=True)

class ChatDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    vector_db_path = db.Column(db.String(500), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    
    user = db.relationship('User', backref='chat_documents', lazy=True)

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('chat_document.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    document = db.relationship('ChatDocument', backref='messages', lazy=True)
    user = db.relationship('User', backref='chat_messages', lazy=True)

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
        try:
            email = request.form['email']
            username = request.form['username']
            password = request.form['password']
            if len(password) < 6:
                flash('Mật khẩu phải có ít nhất 6 ký tự!', 'error')
                return redirect(url_for('register'))
            role = request.form['role']

            # Kiểm tra username và email đã tồn tại
            existing_user = User.query.filter_by(username=username).first()
            existing_email = User.query.filter_by(email=email).first()
            
            if existing_user:
                flash('Tên đăng nhập đã tồn tại. Vui lòng chọn tên đăng nhập khác!', 'error')
                return redirect(url_for('register'))
            if existing_email:
                flash('Email đã được sử dụng. Vui lòng dùng email khác!', 'error')
                return redirect(url_for('register'))

            # Chỉ cho phép email dạng chuẩn, không Unicode, không ký tự đặc biệt ngoài @._-
            email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
            if not re.match(email_pattern, email):
                flash('Email không hợp lệ! Chỉ cho phép ký tự a-z, 0-9, @, ., _, - và không dấu.', 'error')
                return redirect(url_for('register'))

            # Mã hóa mật khẩu
            hashed_password = generate_password_hash(password)
            
            # Tạo user mới
            new_user = User(
                email=email,
                username=username,
                password=hashed_password,
                role=role
            )
            db.session.add(new_user)
            db.session.flush()

            # Tạo profile cho user
            profile = UserProfile(
                user_id=new_user.id,
                full_name=username
            )
            db.session.add(profile)
            db.session.commit()

            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('login'))

        except Exception as e:
            db.session.rollback()
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
    
    # Lấy danh sách các bài kiểm tra đã hết hạn
    now = datetime.now()
    quizzes_expired = Quiz.query.filter_by(teacher_id=teacher_id).filter(Quiz.end_time < now).all()
    
    return render_template('teacher_dashboard.html',
                         total_quizzes=total_quizzes,
                         total_students=total_students,
                         recent_quizzes=recent_quizzes,
                         quizzes_expired=quizzes_expired)

def generate_quiz_code():
    """Generate a random 4-character quiz code"""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase, k=4))
        if not Quiz.query.filter_by(quiz_code=code).first():
            return code

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_pdf_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in PDF_EXTENSIONS

# Chatbot helper functions
def load_llm():
    model_file = "models/vinallama-7b-chat_q5_0.gguf"
    llm = CTransformers(
        model=model_file,
        model_type="llama",
        max_new_tokens=1024,
        temperature=0.01
    )
    return llm

def create_prompt():
    template = """<|im_start|>system\nSử dụng thông tin sau đây để trả lời câu hỏi. Nếu bạn không biết câu trả lời, hãy nói không biết, đừng cố tạo ra câu trả lời\n
    {context}<|im_end|>\n<|im_start|>user\n{question}<|im_end|>\n<|im_start|>assistant"""
    prompt = PromptTemplate(template=template, input_variables=["context", "question"])
    return prompt

def create_qa_chain(prompt, llm, db):
    llm_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={"k": 3}, max_tokens_limit=1024),
        return_source_documents=False,
        chain_type_kwargs={'prompt': prompt}
    )
    return llm_chain

def create_vector_db_from_pdf(pdf_path, vector_db_path):
    try:
        # Load PDF
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        
        # Split text
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=50)
        chunks = text_splitter.split_documents(documents)
        
        # Create embeddings
        embedding_model = GPT4AllEmbeddings(model_file="models/all-MiniLM-L6-v2-f16.gguf")
        
        # Create vector database
        db = FAISS.from_documents(chunks, embedding_model)
        db.save_local(vector_db_path)
        
        return True
    except Exception as e:
        print(f"Error creating vector database: {e}")
        return False

def load_vector_db(vector_db_path):
    try:
        embedding_model = GPT4AllEmbeddings(model_file="models/all-MiniLM-L6-v2-f16.gguf")
        db = FAISS.load_local(vector_db_path, embedding_model, allow_dangerous_deserialization=True)
        return db
    except Exception as e:
        print(f"Error loading vector database: {e}")
        return None

@app.route('/create_quiz', methods=['GET', 'POST'])
def create_quiz():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if user.role != 'teacher':
        flash('Only teachers can create quizzes')
        return redirect(url_for('home'))

    if request.method == 'POST':
        try:
            # Tạo bài kiểm tra mới
            title = request.form['title']
            start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            if end_time <= start_time:
                flash('Thời gian kết thúc phải sau thời gian bắt đầu!', 'danger')
                return redirect(url_for('create_quiz'))
            duration = int(request.form['duration'])
            #max_attempts = request.form.get('max_attempts')  # Lấy giá trị max_attempts từ form
            #is_public = request.form.get('is_public') == 'on'  # Lấy giá trị is_public từ form
            max_attempts = request.form['max_attempts'] if request.form['max_attempts'] else None
            is_public = 'is_public' in request.form
            
            # Tạo mã quiz ngẫu nhiên
            import random, string
            def generate_quiz_code(length=6):
                return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
            
            quiz = Quiz(
                title=title,
                teacher_id=session['user_id'],
                start_time=start_time,
                end_time=end_time,
                duration=duration,
                max_attempts=int(max_attempts) if max_attempts else None,  # Chuyển đổi sang số nếu có giá trị
                is_public=is_public,  # Thêm trường is_public
                quiz_code=generate_quiz_code()
            )
            
            db.session.add(quiz)
            db.session.flush()
            
            # Lấy dữ liệu từ form
            questions = request.form.getlist('questions[]')
            question_types = request.form.getlist('question_types[]')
            correct_answers = request.form.getlist('correct_answers[]')
            question_images = request.files.getlist('question_images[]')
            
            # Thêm câu hỏi và câu trả lời
            for i in range(len(questions)):
                # Process image upload
                image_path = None
                if question_images and i < len(question_images):
                    image = question_images[i]
                    if image and image.filename != '':
                        if allowed_file(image.filename):
                            filename = secure_filename(image.filename)
                            unique_filename = f"{quiz.id}_{i}_{filename}"
                            upload_folder = app.config['UPLOAD_FOLDER']
                            os.makedirs(upload_folder, exist_ok=True)
                            file_path = os.path.join(upload_folder, unique_filename)
                            image.save(file_path)
                            image_path = f"uploads/question_images/{unique_filename}"

                question = Question(
                    quiz_id=quiz.id,
                    question_text=questions[i],
                    question_type=question_types[i],
                    correct_answer=correct_answers[i],
                    image_path=image_path
                )
                db.session.add(question)
                db.session.flush()
                
                # if question_types[i] == 'multiple_choice':
                #     # Debug option keys
                #     print(f"Creating answers for question {i+1}: {questions[i]}")
                    
                #     for j in range(1,5):
                #         option_key = f'option{j}_{i}[]'
                #         options = request.form.getlist(option_key)
                #         print(f"Option key: {option_key}, Values: {options}")
                        
                #         if options and len(options) > 0 and options[0].strip():
                #             answer = Answer(
                #                 question_id=question.id,
                #                 answer_text=options[0]
                #             )
                #             db.session.add(answer)
                #             print(f"Added answer: {options[0]}")
                if question_types[i] == 'multiple_choice':
                    options1 = request.form.getlist('option1[]')
                    options2 = request.form.getlist('option2[]')
                    options3 = request.form.getlist('option3[]')
                    options4 = request.form.getlist('option4[]')

                    options = [
                        options1[i] if i < len(options1) else "",
                        options2[i] if i < len(options2) else "",
                        options3[i] if i < len(options3) else "",
                        options4[i] if i < len(options4) else "",
                    ]

                    for opt_text in options:
                        if opt_text.strip():
                            answer = Answer(
                                question_id=question.id,
                                answer_text=opt_text
                            )
                            db.session.add(answer)

            
            db.session.commit()
            flash(f'Quiz created successfully! Quiz Code: {quiz.quiz_code}')
            return redirect(url_for('manage_quizzes'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Có lỗi xảy ra khi tạo bài kiểm tra: {str(e)}', 'danger')
            return redirect(url_for('create_quiz'))
    
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
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để xem lịch sử!')
        return redirect(url_for('login'))
    
    if session['role'] == 'student':
        results = QuizResult.query.filter_by(student_id=session['user_id']).all()
        return render_template('history.html', results=results, datetime=datetime)
    else:
        quizzes = Quiz.query.filter_by(teacher_id=session['user_id']).all()
        return render_template('history.html', quizzes=quizzes, datetime=datetime)

@app.route('/view-quiz/<int:quiz_id>')
def view_quiz(quiz_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    user = User.query.get(session['user_id'])
    
    # Kiểm tra quyền truy cập
    if user.role != 'teacher' or quiz.teacher_id != user.id:
        flash('Bạn không có quyền truy cập bài kiểm tra này!')
        return redirect(url_for('home'))
    
    # Lấy danh sách câu hỏi của bài kiểm tra
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    return render_template('view_quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz/edit/<int:quiz_id>', methods=['GET', 'POST'])
def edit_quiz(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền truy cập trang này!')
        return redirect(url_for('home'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        try:
            # Cập nhật thông tin cơ bản của quiz
            quiz.title = request.form['title']
            quiz.start_time = datetime.strptime(request.form['start_time'], '%Y-%m-%dT%H:%M')
            quiz.end_time = datetime.strptime(request.form['end_time'], '%Y-%m-%dT%H:%M')
            if quiz.end_time <= quiz.start_time:
                flash('Thời gian kết thúc phải sau thời gian bắt đầu!', 'danger')
                return redirect(url_for('edit_quiz', quiz_id=quiz.id))
            quiz.duration = int(request.form['duration'])
            quiz.max_attempts = int(request.form['max_attempts']) if request.form['max_attempts'] else None
            
            # Xử lý xóa câu hỏi đã đánh dấu để xóa
            questions_to_delete = request.form.get('questions_to_delete', '')
            if questions_to_delete:
                question_ids = [int(id) for id in questions_to_delete.split(',')]
                for question_id in question_ids:
                    question = Question.query.get(question_id)
                    if question and question.quiz_id == quiz.id:
                        # Xóa tất cả câu trả lời liên quan
                        Answer.query.filter_by(question_id=question.id).delete()
                        # Xóa câu hỏi
                        db.session.delete(question)
            
            # Cập nhật hoặc thêm câu hỏi mới
            questions = request.form.getlist('questions[]')
            question_types = request.form.getlist('question_types[]')
            correct_answers = request.form.getlist('correct_answers[]')
            
            # Xóa các câu hỏi không còn trong form
            existing_questions = Question.query.filter_by(quiz_id=quiz.id).all()
            for question in existing_questions:
                if str(question.id) not in request.form.getlist('question_ids[]'):
                    Answer.query.filter_by(question_id=question.id).delete()
                    db.session.delete(question)
            
            # Thêm hoặc cập nhật câu hỏi
            for i in range(len(questions)):
                question_id = request.form.getlist('question_ids[]')[i] if i < len(request.form.getlist('question_ids[]')) else None
                
                if question_id:
                    # Cập nhật câu hỏi hiện có
                    question = Question.query.get(int(question_id))
                    if question and question.quiz_id == quiz.id:
                        question.question_text = questions[i]
                        question.question_type = question_types[i]
                        question.correct_answer = correct_answers[i]
                        
                        # Xóa câu trả lời cũ nếu là câu hỏi trắc nghiệm
                        if question_types[i] == 'multiple_choice':
                            Answer.query.filter_by(question_id=question.id).delete()
                else:
                    # Tạo câu hỏi mới
                    question = Question(
                        quiz_id=quiz.id,
                        question_text=questions[i],
                        question_type=question_types[i],
                        correct_answer=correct_answers[i],
                        image_path=''
                    )
                    db.session.add(question)
                    db.session.flush()
                
                # Thêm các lựa chọn cho câu hỏi trắc nghiệm
                if question_types[i] == 'multiple_choice':
                    for j in range(1, 5):
                        option = request.form.getlist(f'option{j}[]')[i]
                        if option:
                            answer = Answer(
                                question_id=question.id,
                                answer_text=option
                            )
                            db.session.add(answer)
            
            db.session.commit()
            flash('Bài kiểm tra đã được cập nhật thành công!', 'success')
            return redirect(url_for('manage_quizzes'))
            
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi cập nhật bài kiểm tra!', 'error')
            print(f"Error: {str(e)}")
    
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
    
    try:
        # Xóa các kết quả bài kiểm tra trước
        QuizResult.query.filter_by(quiz_id=quiz_id).delete()
        
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
    except Exception as e:
        db.session.rollback()
        flash(f'Có lỗi xảy ra khi xóa bài kiểm tra: {str(e)}')
    
    return redirect(url_for('manage_quizzes'))

@app.route('/search')
def search_quiz():
    keyword = request.args.get('keyword', '')
    if not keyword:
        return redirect(url_for('home'))
    
    # Tìm kiếm tất cả bài kiểm tra và lấy thông tin giáo viên
    quizzes = Quiz.query.join(User, Quiz.teacher_id == User.id)\
                        .outerjoin(UserProfile, User.id == UserProfile.user_id)\
                        .add_columns(User.username, UserProfile.full_name)\
                        .filter(Quiz.title.ilike(f'%{keyword}%'))\
                        .all()
    
    # Chuyển đổi kết quả thành danh sách quiz với thông tin giáo viên
    quiz_list = []
    for quiz, username, full_name in quizzes:
        quiz.teacher_name = full_name if full_name else username
        quiz_list.append(quiz)
    
    return render_template('search_results.html', 
                         quizzes=quiz_list, 
                         keyword=keyword)

@app.route('/join_quiz', methods=['GET', 'POST'])
def join_quiz():
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để tham gia bài kiểm tra!', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        quiz_code = request.form.get('quiz_code')
        quiz_id = request.form.get('quiz_id')

        # Nếu có quiz_id từ form (từ trang tìm kiếm)
        if quiz_id:
            quiz = Quiz.query.get(quiz_id)
            if not quiz or quiz.quiz_code != quiz_code:
                flash('Mã bài kiểm tra không đúng!', 'error')
                return redirect(url_for('search_quiz', keyword=request.args.get('keyword', '')))
        else:
            # Tìm kiếm bài kiểm tra bằng mã (từ trang chủ)
            quiz = Quiz.query.filter_by(quiz_code=quiz_code).first()
            if not quiz:
                flash('Mã bài kiểm tra không tồn tại!', 'error')
                return redirect(url_for('join_quiz'))

        # Kiểm tra thời gian
        current_time = datetime.now()
        if current_time < quiz.start_time:
            flash('Bài kiểm tra chưa bắt đầu!', 'error')
            return redirect(request.referrer or url_for('home'))
        
        if current_time > quiz.end_time:
            flash('Bài kiểm tra đã kết thúc!', 'error')
            return redirect(request.referrer or url_for('home'))

        # Kiểm tra số lần làm bài
        if quiz.max_attempts:
            attempt_count = QuizResult.query.filter_by(
                quiz_id=quiz.id,
                student_id=session['user_id']
            ).count()
            
            if attempt_count >= quiz.max_attempts:
                flash(f'Bạn đã vượt quá số lần làm bài cho phép ({quiz.max_attempts} lần)!', 'error')
                return redirect(request.referrer or url_for('home'))

        # Chuyển hướng đến trang làm bài với mã bài kiểm tra
        return redirect(url_for('take_quiz', quiz_id=quiz.id, quiz_code=quiz_code))

    return render_template('join_quiz.html')

@app.route('/take_quiz/<int:quiz_id>')
def take_quiz(quiz_id):
    if 'user_id' not in session:
        flash('Vui lòng đăng nhập để làm bài kiểm tra!', 'error')
        return redirect(url_for('login'))

    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra quyền truy cập
    if session['role'] == 'student':
        if not quiz.is_public:
            # Nếu là bài kiểm tra riêng tư, kiểm tra mã
            quiz_code = request.args.get('quiz_code')
            if not quiz_code or quiz_code != quiz.quiz_code:
                flash('Bài kiểm tra này ở chế độ riêng tư. Vui lòng sử dụng mã bài kiểm tra để tham gia!', 'error')
                return redirect(url_for('join_quiz'))

    # Kiểm tra thời gian
    current_time = datetime.now()  # Sử dụng datetime.now() thay vì utcnow()
    if current_time < quiz.start_time:
        flash('Bài kiểm tra chưa bắt đầu!', 'error')
        return redirect(url_for('home'))
    
    if current_time > quiz.end_time:
        flash('Bài kiểm tra đã kết thúc!', 'error')
        return redirect(url_for('home'))

    # Kiểm tra số lần làm bài
    if quiz.max_attempts:
        attempt_count = QuizResult.query.filter_by(
            quiz_id=quiz.id,
            student_id=session['user_id']
        ).count()
        
        if attempt_count >= quiz.max_attempts:
            flash(f'Bạn đã vượt quá số lần làm bài cho phép ({quiz.max_attempts} lần)!', 'error')
            return redirect(url_for('home'))

    # Lấy danh sách câu hỏi của bài kiểm tra
    #questions = Question.query.filter_by(quiz_id=quiz_id).all()
    # Dùng joinedload để lấy luôn answers của mỗi question
    questions = Question.query.filter_by(quiz_id=quiz.id)\
        .options(joinedload(Question.answers))\
        .all()
    # Debug: In ra số lượng câu hỏi
    print(f"Number of questions: {len(questions)}")
    for q in questions:
        print(f"Question {q.id}: {q.question_text}")
        print(f"Type: {q.question_type}")
        if q.question_type == 'multiple_choice':
            print("Answers:")
            for a in q.answers:
                print(f"- {a.answer_text}")

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
        #answers[question.id] = answer
        print(f"Câu hỏi {question.id} - Câu trả lời nhận được: {answer}")  # Debug
        if answer is None:
            print(f"LỖI: Câu trả lời cho câu hỏi {question.id} không nhận được từ form!")
        # Lưu câu trả lời vào database
        student_answer = StudentAnswer(
            quiz_id=quiz_id,
            student_id=session['user_id'],
            question_id=question.id,
            answer_text=answer or ""
        )
        db.session.add(student_answer)
        
        # Kiểm tra đáp án
        if question.question_type == 'multiple_choice':
            #selected_answer = Answer.query.get(int(answer)) if answer else None
            selected_answer = db.session.get(Answer, int(answer)) if answer else None

            if selected_answer and selected_answer.answer_text.strip() == question.correct_answer.strip():
                score += 1
        else:  # fill_in_blank
            if answer and answer.strip().lower() == question.correct_answer.strip().lower():
                score += 1
    
    # Tính điểm theo thang 10
    final_score = (score / total_questions) * 10 if total_questions > 0 else 0

    
    # Lưu kết quả vào database
    quiz_result = QuizResult(
        quiz_id=quiz_id,
        student_id=session['user_id'],
        score=final_score
    )
    db.session.add(quiz_result)
    db.session.commit()
    #saved_result = QuizResult.query.filter_by(quiz_id=quiz_id, student_id=session['user_id']).first()
    #print(f"Điểm lưu vào DB: {saved_result.score if saved_result else 'Không tìm thấy'}")

    

    return redirect(url_for('results_page', quiz_id=quiz_id))
    
   
@app.route('/results/<int:quiz_id>')
def results_page(quiz_id):
    if 'user_id' not in session:
        flash('Bạn cần đăng nhập để xem kết quả!')
        return redirect(url_for('login'))


    quiz = Quiz.query.get_or_404(quiz_id)

    # Lấy kết quả của user
    result = QuizResult.query.filter_by(
        quiz_id=quiz_id, 
        student_id=session['user_id']
    ).order_by(QuizResult.id.desc()).first()
    
    
    if not result:
        flash('Không tìm thấy kết quả bài kiểm tra của bạn.')
        return redirect(url_for('home'))

    # Lấy danh sách câu hỏi
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    # Lấy câu trả lời của học sinh
   
    # Truy vấn tất cả câu trả lời của học sinh trong bài quiz
    student_answers = StudentAnswer.query.filter_by(
        quiz_id=quiz_id, 
        student_id=session["user_id"]
    ).all()

    # Lấy toàn bộ câu trả lời từ bảng Answer trước (để tránh truy vấn nhiều lần trong vòng lặp)
    all_answers = {a.id: a.answer_text for a in Answer.query.all()}

    # Tạo dict: {question_id: answer_text}
    student_answers_dict = {}
    for answer in student_answers:
        question = Question.query.get(answer.question_id)
        if not question:
            continue  # Bỏ qua nếu câu hỏi không tồn tại

        if question.question_type == 'multiple_choice':
            # Trắc nghiệm: answer_text là ID, tra ra text từ all_answers
            answer_text = all_answers.get(int(answer.answer_text), "Chưa trả lời")
        else:
            # Fill-in-the-blank: answer_text là text người dùng nhập vào
            answer_text = answer.answer_text

        student_answers_dict[answer.question_id] = answer_text

    # So sánh và tạo danh sách kết quả
    results = []
    for question in questions:
        user_answer = student_answers_dict.get(question.id, "Chưa trả lời")
        is_correct = False

        if user_answer != "Chưa trả lời":
            if question.question_type == 'multiple_choice':
                is_correct = user_answer.strip() == question.correct_answer.strip()
            else:  # fill_in_blank
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()

        results.append((
            Markup(question.question_text),
            Markup(user_answer),
            Markup(question.correct_answer),
            is_correct,
            question.question_type
        ))


    return render_template(
        'results_after.html', 
        quiz=quiz, 
        score=result.score, 
        total_questions=len(questions),
        results=results
    )



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

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    user_profile = UserProfile.query.filter_by(user_id=user.id).first()
    
    if not user_profile:
        user_profile = UserProfile(user_id=user.id)
        db.session.add(user_profile)
        db.session.commit()
    
    return render_template('profile.html', user=user, profile=user_profile)

@app.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    profile = UserProfile.query.filter_by(user_id=user.id).first()
    
    if request.method == 'POST':
        # Cập nhật thông tin profile
        profile.full_name = request.form.get('full_name')
        profile.phone = request.form.get('phone')
        profile.address = request.form.get('address')
        profile.bio = request.form.get('bio')

        # Xử lý upload avatar
        avatar_file = request.files.get('avatar')
        if avatar_file and avatar_file.filename != '':
            filename = secure_filename(avatar_file.filename)
            upload_folder = os.path.join('static', 'uploads', 'avatars')
            os.makedirs(upload_folder, exist_ok=True)
            file_path = os.path.join(upload_folder, f'{user.id}_{filename}')
            avatar_file.save(file_path)
            profile.avatar = f'uploads/avatars/{user.id}_{filename}'
        
        db.session.commit()
        flash('Cập nhật thông tin thành công!')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=user, profile=profile)

@app.route('/settings')
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('settings.html', user=user)

@app.route('/settings/password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not check_password_hash(user.password, current_password):
        flash('Mật khẩu hiện tại không đúng!')
        return redirect(url_for('settings'))
    
    if new_password != confirm_password:
        flash('Mật khẩu mới không khớp!')
        return redirect(url_for('settings'))
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Đổi mật khẩu thành công!')
    return redirect(url_for('settings'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a unique token
            token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            expires_at = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
            
            # Create password reset token
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # Redirect directly to reset password page
            return redirect(url_for('reset_password', token=token))
        
        flash('Email không tồn tại trong hệ thống.', 'error')
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        flash('Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.', 'error')
        return redirect(url_for('forgot_password'))
    
    if datetime.utcnow() > reset_token.expires_at:
        flash('Link đặt lại mật khẩu đã hết hạn.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Mật khẩu xác nhận không khớp.', 'error')
            return render_template('reset_password.html')
        
        # Update user's password
        reset_token.user.password = generate_password_hash(password)
        reset_token.used = True
        db.session.commit()
        
        flash('Mật khẩu đã được đặt lại thành công. Vui lòng đăng nhập.', 'success')
        return redirect(url_for('login'))
    
    return render_template('reset_password.html')

@app.route('/quiz/<int:quiz_id>/toggle-visibility')
def toggle_quiz_visibility(quiz_id):
    if 'user_id' not in session or session['role'] != 'teacher':
        flash('Bạn không có quyền thực hiện hành động này!')
        return redirect(url_for('home'))
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kiểm tra quyền truy cập
    if quiz.teacher_id != session['user_id']:
        flash('Bạn không có quyền thay đổi trạng thái bài kiểm tra này!')
        return redirect(url_for('manage_quizzes'))
    
    # Đảo ngược trạng thái công khai
    quiz.is_public = not quiz.is_public
    db.session.commit()
    
    status = "công khai" if quiz.is_public else "riêng tư"
    flash(f'Trạng thái bài kiểm tra đã được thay đổi thành {status}!')
    return redirect(url_for('manage_quizzes'))

@app.context_processor
def inject_user_profile():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        profile = UserProfile.query.filter_by(user_id=user.id).first()
        return dict(nav_profile=profile)
    return dict(nav_profile=None)

@app.route('/review_result/<int:result_id>')
def review_result(result_id):
    # Lấy result theo id, kiểm tra quyền truy cập
    result = QuizResult.query.get_or_404(result_id)
    if result.student_id != session.get('user_id'):
        abort(403)
    quiz = result.quiz
    score = result.score

    # Lấy danh sách câu hỏi
    questions = Question.query.filter_by(quiz_id=quiz.id).all()

    # Lấy câu trả lời của học sinh
    student_answers = StudentAnswer.query.filter_by(
        quiz_id=quiz.id,
        student_id=result.student_id
    ).all()

    # Lấy toàn bộ câu trả lời từ bảng Answer trước (để tránh truy vấn nhiều lần trong vòng lặp)
    all_answers = {a.id: a.answer_text for a in Answer.query.all()}

    # Tạo dict: {question_id: answer_text}
    student_answers_dict = {}
    for answer in student_answers:
        question = Question.query.get(answer.question_id)
        if not question:
            continue  # Bỏ qua nếu câu hỏi không tồn tại

        if question.question_type == 'multiple_choice':
            # Trắc nghiệm: answer_text là ID, tra ra text từ all_answers
            try:
                answer_text = all_answers.get(int(answer.answer_text), "Chưa trả lời")
            except Exception:
                answer_text = "Chưa trả lời"
        else:
            # Fill-in-the-blank: answer_text là text người dùng nhập vào
            answer_text = answer.answer_text

        student_answers_dict[answer.question_id] = answer_text

    # So sánh và tạo danh sách kết quả
    results = []
    for question in questions:
        user_answer = student_answers_dict.get(question.id, "Chưa trả lời")
        is_correct = False

        if user_answer != "Chưa trả lời":
            if question.question_type == 'multiple_choice':
                is_correct = user_answer.strip() == question.correct_answer.strip()
            else:  # fill_in_blank
                is_correct = user_answer.strip().lower() == question.correct_answer.strip().lower()

        results.append((
            Markup(question.question_text),
            Markup(user_answer),
            Markup(question.correct_answer),
            is_correct,
            question.question_type
        ))

    return render_template('results_after.html', quiz=quiz, score=score, results=results)

# Chatbot routes
@app.route('/chatbot')
def chatbot():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_documents = ChatDocument.query.filter_by(user_id=session['user_id']).order_by(ChatDocument.uploaded_at.desc()).all()
    return render_template('chatbot.html', documents=user_documents)

@app.route('/chatbot/upload', methods=['POST'])
def upload_document():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if 'file' not in request.files:
        flash('Không có file nào được chọn!', 'error')
        return redirect(url_for('chatbot'))
    
    file = request.files['file']
    if file.filename == '':
        flash('Không có file nào được chọn!', 'error')
        return redirect(url_for('chatbot'))
    
    if file and allowed_pdf_file(file.filename):
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Secure filename
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{filename}"
        
        # Save file
        file_path = os.path.join(app.config['CHATBOT_UPLOAD_FOLDER'], unique_filename)
        os.makedirs(app.config['CHATBOT_UPLOAD_FOLDER'], exist_ok=True)
        file.save(file_path)
        
        # Create vector database
        vector_db_path = os.path.join('vectorstores', f'db_{session_id}')
        
        if create_vector_db_from_pdf(file_path, vector_db_path):
            # Save to database
            chat_document = ChatDocument(
                user_id=session['user_id'],
                filename=unique_filename,
                original_filename=filename,
                file_path=file_path,
                vector_db_path=vector_db_path,
                session_id=session_id
            )
            db.session.add(chat_document)
            db.session.commit()
            
            flash('Tài liệu đã được upload và xử lý thành công!', 'success')
            return redirect(url_for('chat_session', session_id=session_id))
        else:
            # Remove file if vector database creation failed
            if os.path.exists(file_path):
                os.remove(file_path)
            flash('Có lỗi xảy ra khi xử lý tài liệu!', 'error')
    else:
        flash('Chỉ chấp nhận file PDF!', 'error')
    
    return redirect(url_for('chatbot'))

@app.route('/chatbot/session/<session_id>')
def chat_session(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    document = ChatDocument.query.filter_by(session_id=session_id, user_id=session['user_id']).first()
    if not document:
        flash('Không tìm thấy tài liệu!', 'error')
        return redirect(url_for('chatbot'))
    
    messages = ChatMessage.query.filter_by(document_id=document.id).order_by(ChatMessage.created_at.asc()).all()
    return render_template('chat_session.html', document=document, messages=messages)

@app.route('/chatbot/ask', methods=['POST'])
def ask_question():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    question = data.get('question')
    session_id = data.get('session_id')
    
    if not question or not session_id:
        return jsonify({'error': 'Missing question or session_id'}), 400
    
    document = ChatDocument.query.filter_by(session_id=session_id, user_id=session['user_id']).first()
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    try:
        # Load vector database
        db_vector = load_vector_db(document.vector_db_path)
        if not db_vector:
            return jsonify({'error': 'Error loading knowledge base'}), 500
        
        # Load LLM and create chain
        llm = load_llm()
        prompt = create_prompt()
        qa_chain = create_qa_chain(prompt, llm, db_vector)
        
        # Get answer
        response = qa_chain.invoke({"query": question})
        answer = response.get('result', 'Xin lỗi, tôi không thể trả lời câu hỏi này.')
        
        # Save to database
        chat_message = ChatMessage(
            document_id=document.id,
            user_id=session['user_id'],
            question=question,
            answer=answer
        )
        db.session.add(chat_message)
        db.session.commit()
        
        return jsonify({
            'question': question,
            'answer': answer,
            'timestamp': chat_message.created_at.strftime('%H:%M:%S')
        })
        
    except Exception as e:
        print(f"Error processing question: {e}")
        return jsonify({'error': 'Error processing your question'}), 500

@app.route('/chatbot/delete/<session_id>')
def delete_document(session_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    document = ChatDocument.query.filter_by(session_id=session_id, user_id=session['user_id']).first()
    if not document:
        flash('Không tìm thấy tài liệu!', 'error')
        return redirect(url_for('chatbot'))
    
    try:
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete vector database directory
        import shutil
        if os.path.exists(document.vector_db_path):
            shutil.rmtree(document.vector_db_path)
        
        # Delete from database
        ChatMessage.query.filter_by(document_id=document.id).delete()
        db.session.delete(document)
        db.session.commit()
        
        flash('Tài liệu đã được xóa thành công!', 'success')
    except Exception as e:
        flash('Có lỗi xảy ra khi xóa tài liệu!', 'error')
    
    return redirect(url_for('chatbot'))

def main():
    with app.app_context():
        # Chỉ tạo bảng nếu chưa tồn tại
        db.create_all()
    port = int(os.environ.get('PORT', 8080)) # Lấy cổng từ biến môi trường PORT, mặc định là 8080
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    main() 