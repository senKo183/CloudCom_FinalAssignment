from app import app, db, Quiz, Question, Answer, User

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
        
        # Đếm số câu hỏi trong bài kiểm tra
        question_count = Question.query.filter_by(quiz_id=quiz.id).count()
        print(f"Số câu hỏi: {question_count}")
        print("-" * 50) 