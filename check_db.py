from app import app, db, Quiz, Question, Answer, User
from sqlalchemy import text

def check_and_fix_database():
    with app.app_context():
        try:
            # Kiểm tra xem cột max_attempts có tồn tại không
            result = db.session.execute(text("PRAGMA table_info(quiz)"))
            columns = [row[1] for row in result]
            
            if 'max_attempts' not in columns:
                print("Cột max_attempts chưa tồn tại. Đang thêm...")
                # Thêm cột max_attempts
                db.session.execute(text("ALTER TABLE quiz ADD COLUMN max_attempts INTEGER"))
                db.session.commit()
                print("Đã thêm cột max_attempts thành công!")
            else:
                print("Cột max_attempts đã tồn tại.")
                
        except Exception as e:
            print(f"Có lỗi xảy ra: {str(e)}")
            db.session.rollback()

def show_database_info():
    with app.app_context():
        # Kiểm tra số lượng bài kiểm tra
        quiz_count = Quiz.query.count()
        print(f"\nSố lượng bài kiểm tra: {quiz_count}")
        
        # Liệt kê chi tiết các bài kiểm tra
        quizzes = Quiz.query.all()
        print("\nChi tiết các bài kiểm tra:")
        print("-" * 50)
        for quiz in quizzes:
            print(f"ID: {quiz.id}")
            print(f"Tiêu đề: {quiz.title}")
            print(f"Thời gian bắt đầu: {quiz.start_time}")
            print(f"Thời gian kết thúc: {quiz.end_time}")
            print(f"Thời gian làm bài: {quiz.duration} phút")
            print(f"Số lần làm bài tối đa: {quiz.max_attempts if quiz.max_attempts else 'Không giới hạn'}")
            
            # Đếm số câu hỏi trong bài kiểm tra
            question_count = Question.query.filter_by(quiz_id=quiz.id).count()
            print(f"Số câu hỏi: {question_count}")
            print("-" * 50)

if __name__ == '__main__':
    check_and_fix_database()
    show_database_info() 