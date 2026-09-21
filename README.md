NEON // IMAGE LAB

Web chỉnh sửa ảnh local bằng FastAPI + OpenCV, giao diện dark cyberpunk/pixel.

Chức năng

Import ảnh JPG / PNG / WEBP / BMP.

Preview ảnh gốc và ảnh sau xử lý song song.

Realtime preview khi kéo slider (frontend debounce request tới FastAPI).

Kỹ thuật HSV:

Hue: -180° đến +180°.

Saturation: -100 đến +100.

Value: -100 đến +100.

Kỹ thuật Histogram / tonal range:

Blacks, Shadows, Midtones, Highlights, Whites: -100 đến +100.

Reset ảnh về trạng thái ban đầu.

Export PNG ở độ phân giải gốc.

Luminance histogram realtime ở frontend.

Cấu trúc

cyberpunk_image_lab/
├─ main.py
├─ requirements.txt
├─ algorithms/
│  ├─ __init__.py
│  ├─ hsv.py
│  └─ histogram.py
├─ templates/
│  └─ index.html
├─ static/
│  ├─ style.css
│  └─ app.js
├─ uploads/
└─ exports/

Cài đặt

python -m venv .venv

Windows:

.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload

Sau đó mở:

http://127.0.0.1:8000

Luồng xử lý

Browser
  ↓ Import
POST /api/upload
  ↓ lưu ảnh gốc bằng UUID
Frontend nhận image_id
  ↓ kéo slider
POST /api/process + JSON settings
  ↓
FastAPI
  ├─ technique = hsv       → algorithms/hsv.py
  └─ technique = histogram → algorithms/histogram.py
  ↓
OpenCV xử lý preview
  ↓ JPEG
Browser cập nhật ảnh OUTPUT

Export:
POST /api/export → xử lý ảnh gốc full-resolution → PNG download

Ghi chú thuật toán HSV

OpenCV lưu Hue trong khoảng 0..179, đại diện cho góc màu 0..358°. Vì vậy slider Hue theo độ được chia 2 trước khi cộng vào channel H.

Ghi chú Histogram

Phần Histogram ở đây là tonal adjustment kiểu photo editor. Ảnh được chuyển sang LAB và thao tác trên kênh L. Năm vùng sáng tối dùng các weight Gaussian chồng lấn để tránh banding/ranh giới cứng.
