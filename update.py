from app import app, db, Question

with app.app_context():
    questions = Question.query.filter(Question.image_path == None).all()

    for q in questions:
        q.image_path = 'default.jpg'

    db.session.commit()
    print(f"✅ Đã cập nhật {len(questions)} question có image_path = None.")
