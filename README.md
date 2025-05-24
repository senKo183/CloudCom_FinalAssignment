#   QUIZ APP

## 1. THÔNG TIN NHÓM

- [Lê Hà Tú My] - [lehatmy@gmail.com]
- [Nguyễn Quang Mạnh] - [nguyenquangmanh120304@gmail.com]
- [Phạm Thị Ngọc Hương] - [pvnhuong2405@gmail.com]
- [Nguyễn Thanh Tường Vy] - [nvy2902@gmail.com]

## 2. MÔ TẢ ĐỀ TÀI

### 2.1. Mô tả tổng quan
[Viết ý tưởng thực hiện đề tài, các vấn đề cần giải quyết và lý do chọn đề tài.]  
- **Ý tưởng thực hiện:**  
  Trong bối cảnh chuyển đổi số trong giáo dục, việc ứng dụng công nghệ vào dạy và học ngày càng trở nên cần thiết. Một trong những nhu cầu cấp thiết là xây dựng một nền tảng kiểm tra trực tuyến thân thiện, dễ sử dụng, đặc biệt hỗ trợ cho việc kiểm tra kiến thức các môn học có nhiều công thức như Toán học.  
  Từ thực tế đó, nhóm em đề xuất xây dựng một ứng dụng web có tên là Quiz App, cho phép giáo viên tạo đề kiểm tra, nhập các câu hỏi có chứa công thức toán (hỗ trợ LaTeX), và học sinh có thể làm bài trực tiếp trên giao diện đơn giản, dễ tiếp cận.  

- **Ứng dụng này hướng đến mục tiêu:** 
    + Hỗ trợ giáo viên dễ dàng tạo các đề trắc nghiệm/tự luận có hỗ trợ nhập công thức toán học dạng LaTex.  
    + Học sinh có thể làm bài mọi lúc mọi nơi, tiết kiệm thời gian và giấy mực.  
    + Tự động chấm điểm và lưu trữ kết quả.
- **Các vấn đề cần giải quyết:**
    + Giới hạn thời gian cho bài kiểm tra: thời gian bắt đầu,kết thúc và thời gian làm bài kiểm tra.
    + Thiết kế giao diện đa vai trò:  
        * Phân quyền người dùng gồm giáo viên (admin) và học sinh.  
        * Giáo viên được phép tạo câu hỏi, tạo bài kiểm tra, xem kết quả.  
        * Học sinh chỉ được phép làm bài kiểm tra và xem điểm số.
    + Hỗ trợ tích hợp LaTex vào phần tạo câu hỏi và câu trả lời.
- **Lý do chọn đề tài:**
    + Phù hợp với xu hướng giáo dục: sau dịch COVID-19, việc học online đang dần phổ biến trong hệ thống giáo dục bởi tính hữu ích, cùng với đó hình thức kiểm tra online cũng được áp dụng vào, chính vì thế những ứng dụng như Quiz rất thiết thực.
    + Nhiều giáo viên vẫn gặp khó khăn trong việc tạo đề online có công thức toán học.
    + Tính ứng dụng cao: Ứng dụng có thể mở rộng không chỉ cho môn Toán mà cả Lý, Hóa, và các môn trắc nghiệm khác.
    + Mong muốn giúp các giáo viên có thể tiết kiệm thời gian trong công việc, tự động hóa công việc chấm điểm.
      
### 2.2. Mục tiêu
[Viết các mục tiêu cụ thể của đề tài, những gì bạn muốn đạt được sau khi hoàn thành.]
- Mục tiêu 1: Giáo viên có thể tạo bài kiểm tra/Học sinh có thể làm bài kiểm tra và xem lại điểm số.
- Mục tiêu 2: Ứng dụng có thể tạo tự động câu hỏi và câu trả lời dựa vào file .csv(Có format) mà giáo viên đưa ra.
- Mục tiêu 3: Tích hợp nhập định dạng LaTex khi tạo câu hỏi và câu trả lời.
  
## 3. PHÂN TÍCH THIẾT KẾ

### 3.1. Phân tích yêu cầu
[Viết các yêu cầu chức năng và phi chức năng của hệ thống.]
- Các yêu cầu chức năng:
  + Người dùng có thể đăng nhập/đăng kí.   
  + Giáo viên có thể tạo bài kiểm tra với công thức toán học viết bằng LaTex.  
  + Học sinh làm bài trắc nghiệm và nhận kết quả sau khi làm bài xong.  
  + Chấm điểm tự động.
    
- Các yêu cầu phi chức năng:
  + Giao diện đơn giản và dễ sử dụng.
  + Hiển thị đúng các công thức toán học.

### 3.2. Đặc tả yêu cầu
[Viết chi tiết các yêu cầu chức năng và phi chức năng, có thể sử dụng sơ đồ hoặc bảng biểu để minh họa.]
- [Đặc tả chức năng 1]
- [Đặc tả chức năng 2]

### 3.2. Thiết kế hệ thống
- Use case diagram
- Thiết kế CSDL
- Thiết kế giao diện (screenshot các màn hình chính/wireframe)

## 4. CÔNG CỤ VÀ CÔNG NGHỆ SỬ DỤNG

- Ngôn ngữ lập trình: [Python,JS]
- Framework: [Flask, MathJax]
- Cơ sở dữ liệu: [SQLite]
- IDE: [Visual Studio Code]

## 5. TRIỂN KHAI
[Viết các bước triển khai, cách thức cài đặt và chạy ứng dụng.]
- **Các bước triển khai:**

### 🔹 Bước 1: Phân tích yêu cầu và chức năng

* Xác định đối tượng sử dụng: **giáo viên** và **học sinh**.
* Các chức năng chính:

  * Giáo viên tạo bài kiểm tra có chứa công thức Toán.
  * Học sinh đăng nhập và làm bài kiểm tra.
  * Tự động chấm điểm và hiển thị kết quả.

---

### 🔹 Bước 2: Thiết kế hệ thống

* **Use Case Diagram**: xác định các tác nhân và hành động tương ứng.
* **Thiết kế cơ sở dữ liệu**: tạo các bảng như `users`, `quizzes`, `questions`, `answers`, `results`,...
* **Thiết kế giao diện**: giao diện đơn giản, dễ sử dụng,cho phép sinh viên thêm avatar cho tài khoản, hỗ trợ hiển thị công thức Toán học với MathJax.
---

### 🔹 Bước 3: Xây dựng ứng dụng

* **Backend (Python - Flask)**:

  * Xử lý logic: tạo bài, lưu trữ câu hỏi, tính điểm,...
  * Kết nối với database (SQLite).
* **Frontend (HTML/CSS + JS)**:

  * Hiển thị câu hỏi và công thức toán học.
  * Tạo và chỉnh sửa giao diện thân thiện, rõ ràng, dễ sử dụng.
  * Tích hợp **MathJax** để hiển thị công thức Toán.

---

### 🔹 Bước 4: Kiểm thử chức năng

* Kiểm thử đăng nhập, tạo bài, làm bài, tính điểm,xem điểm.
* Kiểm tra hiển thị công thức toán có đúng định dạng.
* Kiểm tra dữ liệu lưu đúng vào cơ sở dữ liệu.

---

### 🔹 Bước 5: Triển khai ứng dụng cục bộ

* Cài đặt thư viện bằng `pip install -r requirements.txt`
* Chạy ứng dụng bằng `python app.py`
* Truy cập qua `http://localhost:5000`

---

### 🔹 Bước 6: Triển khai ứng dụng.

* Triển khai ứng dụng bằng Docker
---

- **Cách thức cài đặt:**   
  + Yêu cầu: Phiên bản `python` dưới **3.13** (khuyến khích sử dụng phiên bản 3.10, 3.11, 3.12)
  + **Hướng dẫn cài đặt:**  
    **Kích hoạt môi trường ảo:**
    ```
    python -m venv venv
    venv/scripts/activate
    ```
    **Cài đặt thư viện:**
    ```
    pip install -r requirementss.txt
    ```
    **Chạy ứng dụng :**
    ```
    python app.py
    ```
## 6. KIỂM THỬ
- Thực hiện kiểm thử chức năng (Functional Testing)
- Kiểm thử hiệu năng (Performance Testing)

## 7. KẾT QUẢ
[Viết các kết quả đạt được sau khi hoàn thành đề tài, có thể sử dụng hình ảnh hoặc bảng biểu để minh họa.]

### 7.1. Kết quả đạt được
- [Kết quả 1]
- [Kết quả 2]

### 7.2. Kết quả chưa đạt được
- [Kết quả chưa đạt được 1]
- [Kết quả chưa đạt được 2]

### 7.3. Hướng phát triển (optional)
[Bạn có muốn phát triển tiếp đề tài này hay không? Nếu có, hãy viết rõ hướng phát triển tiếp theo của đề tài.]

Hướng phát triển ứng dụng MathQuiz trong tương lai:  
  ●	Tích hợp AI chấm tự luận.  
  ●	Gợi ý học phần yếu cần luyện tập (theo lịch sử bài làm).  
  ●	Tích hợp live quiz hoặc thi đấu giữa các học sinh.    
  ●	Phát hành phiên bản mobile (React Native).   
  ●	 Hệ thống phòng thi bảo mật, chống gian lận (camera, giới hạn tab…).  

## 8. TÀI LIỆU THAM KHẢO
- [https://github.com/thepasterover/flask-quiz-app]
- [https://flask.palletsprojects.com/en/stable/]
- [https://flutter.dev]
- [https://dart.dev]
