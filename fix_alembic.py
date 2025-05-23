import sqlite3

# Kết nối tới database
conn = sqlite3.connect("instance/mathquiz.db")
cursor = conn.cursor()

# Xóa nội dung trong bảng alembic_version
cursor.execute("DELETE FROM alembic_version")

# Lưu thay đổi và đóng kết nối
conn.commit()
conn.close()

print("Đã xóa bảng alembic_version.")
