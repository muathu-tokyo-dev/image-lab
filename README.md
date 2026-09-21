# 🌌 NEON // IMAGE LAB

> **Local Image Processing Web Application**
> Built with **FastAPI + OpenCV + JavaScript**

**NEON // IMAGE LAB** là một ứng dụng web chỉnh sửa ảnh chạy hoàn toàn trên máy local, sử dụng **FastAPI** làm backend và **OpenCV** để xử lý ảnh.

Ứng dụng cung cấp giao diện **Dark Cyberpunk / Pixel**, cho phép người dùng import ảnh, lựa chọn kỹ thuật xử lý và theo dõi kết quả gần như **realtime** khi thay đổi các thông số.

---

## ✨ Features

### 📥 Import Image

Hỗ trợ các định dạng ảnh phổ biến:

* JPG / JPEG
* PNG
* WEBP
* BMP

Ảnh được upload lên FastAPI và lưu tạm bằng một **UUID riêng biệt**.

---

### 🖼️ Before / After Preview

Hai khung ảnh được hiển thị song song:

```text
┌─────────────────────┐    ┌─────────────────────┐
│                     │    │                     │
│    ORIGINAL IMAGE   │    │    OUTPUT IMAGE     │
│                     │    │                     │
└─────────────────────┘    └─────────────────────┘
```

* **Original Image:** ảnh gốc.
* **Output Image:** ảnh sau khi áp dụng thuật toán.

Kết quả được cập nhật khi người dùng thay đổi slider.

---

## ⚡ Realtime Processing

Khi kéo slider:

```text
Slider changed
      ↓
Frontend Debounce
      ↓
POST /api/process
      ↓
FastAPI
      ↓
OpenCV Processing
      ↓
JPEG Preview
      ↓
Update OUTPUT Image
```

Frontend sử dụng **debounce request** nhằm hạn chế gửi quá nhiều request khi slider được kéo liên tục.

Ảnh gốc chỉ cần upload **một lần**.

Sau đó frontend chỉ gửi:

* `image_id`
* kỹ thuật đang sử dụng
* các thông số hiện tại

đến backend.

---

# 🎨 Image Processing Techniques

Ứng dụng hiện hỗ trợ hai nhóm kỹ thuật:

```text
IMAGE PROCESSING
│
├── HSV
│   ├── Hue
│   ├── Saturation
│   └── Value
│
└── HISTOGRAM / TONAL RANGE
    ├── Blacks
    ├── Shadows
    ├── Midtones
    ├── Highlights
    └── Whites
```

---

## 🌈 HSV Adjustment

HSV là không gian màu gồm:

* **Hue** — sắc độ màu.
* **Saturation** — độ bão hòa màu.
* **Value** — độ sáng.

Các thông số trong ứng dụng:

| Parameter  |           Range | Chức năng              |
| ---------- | --------------: | ---------------------- |
| Hue        | `-180° → +180°` | Thay đổi sắc màu       |
| Saturation |   `-100 → +100` | Tăng / giảm độ rực màu |
| Value      |   `-100 → +100` | Tăng / giảm độ sáng    |

### OpenCV HSV

Ảnh từ OpenCV ban đầu sử dụng:

```text
BGR
```

Khi xử lý HSV:

```text
BGR
 ↓
HSV
 ↓
Modify H / S / V
 ↓
BGR
```

OpenCV lưu Hue trong khoảng:

```text
0 → 179
```

trong khi Hue theo góc màu thông thường là:

```text
0° → 360°
```

Do đó giá trị Hue từ slider được quy đổi:

```text
Hue_OpenCV = Hue_Degree / 2
```

Ví dụ:

```text
Slider Hue = +60°

        ↓

OpenCV Hue Shift = +30
```

Thuật toán được đặt riêng tại:

```text
algorithms/hsv.py
```

---

# 📊 Histogram / Tonal Adjustment

Phần **Histogram** của project được thiết kế theo hướng **tonal adjustment** tương tự các phần mềm chỉnh sửa ảnh.

Người dùng có thể điều chỉnh năm vùng sáng tối:

| Parameter  | Ý nghĩa              |
| ---------- | -------------------- |
| Blacks     | Vùng tối nhất        |
| Shadows    | Vùng bóng tối        |
| Midtones   | Vùng sáng trung bình |
| Highlights | Vùng sáng            |
| Whites     | Vùng sáng nhất       |

Mỗi thông số có khoảng:

```text
-100 → +100
```

---

## 💡 Tonal Processing

Ảnh được chuyển sang không gian màu:

```text
BGR
 ↓
LAB
```

Trong LAB:

```text
L = Lightness
A = Green ↔ Red
B = Blue ↔ Yellow
```

Project chủ yếu thao tác trên:

```text
L Channel
```

để thay đổi độ sáng mà hạn chế làm sai lệch màu sắc.

---

## 📈 Tonal Range Weighting

Năm vùng:

```text
Blacks
Shadows
Midtones
Highlights
Whites
```

không được chia bằng các ngưỡng cứng.

Thay vào đó, project sử dụng các **Gaussian Weight** chồng lấn.

Ví dụ:

```text
Weight
  ▲
1 │      Shadows
  │        /\
  │       /  \       Midtones
  │      /    \        /\
  │_____/______\______/__\____________► Lightness
     Black              Highlight
```

Điều này giúp quá trình chuyển tiếp giữa các vùng sáng tối:

* mềm hơn;
* hạn chế banding;
* tránh xuất hiện ranh giới sáng tối đột ngột.

Thuật toán nằm tại:

```text
algorithms/histogram.py
```

---

# 📉 Realtime Luminance Histogram

Frontend hiển thị **Luminance Histogram** của ảnh output.

Histogram biểu diễn:

```text
Pixel Count
    ▲
    │        █
    │      ███
    │   ███████
    │ ███████████
    └──────────────────────►
      Dark           Bright
       0               255
```

Histogram được cập nhật khi output image thay đổi.

---

# ♻️ Reset Image

Nút **RESET** đưa toàn bộ thông số về:

```text
0
```

và khôi phục OUTPUT về trạng thái ảnh ban đầu.

Việc xử lý luôn được thực hiện theo nguyên tắc:

```text
ORIGINAL IMAGE
      +
CURRENT SETTINGS
      ↓
NEW OUTPUT
```

Không xử lý theo dạng:

```text
Output 1
   ↓
Output 2
   ↓
Output 3
   ↓
...
```

nhằm hạn chế giảm chất lượng ảnh qua nhiều lần chỉnh sửa.

---

# 📤 Export

Khi chỉnh sửa hoàn tất, người dùng có thể export ảnh dưới dạng:

```text
PNG
```

Preview trên giao diện có thể được resize để tăng tốc độ xử lý.

Tuy nhiên khi export:

```text
Original Full Resolution Image
            ↓
Apply Current Settings
            ↓
        OpenCV
            ↓
     Full Resolution PNG
```

Backend xử lý lại trực tiếp từ **ảnh gốc ở độ phân giải ban đầu**.

---

# 🏗️ Project Structure

```text
cyberpunk_image_lab/
│
├── main.py
├── requirements.txt
│
├── algorithms/
│   ├── __init__.py
│   ├── hsv.py
│   └── histogram.py
│
├── templates/
│   └── index.html
│
├── static/
│   ├── style.css
│   └── app.js
│
├── uploads/
│
└── exports/
```

### Thành phần chính

```text
main.py
```

FastAPI server, chịu trách nhiệm:

* upload ảnh;
* nhận thông số từ frontend;
* gọi thuật toán tương ứng;
* trả preview;
* export ảnh.

---

```text
algorithms/hsv.py
```

Xử lý:

```text
Hue
Saturation
Value
```

---

```text
algorithms/histogram.py
```

Xử lý:

```text
Blacks
Shadows
Midtones
Highlights
Whites
```

---

```text
templates/index.html
```

Giao diện chính của website.

---

```text
static/style.css
```

Thiết kế giao diện:

```text
Dark
Cyberpunk
Pixel-inspired
Neon UI
```

---

```text
static/app.js
```

Quản lý:

* import ảnh;
* slider;
* realtime request;
* debounce;
* preview;
* histogram;
* reset;
* export.

---

# 🔄 System Architecture

```text
                 ┌──────────────────────┐
                 │       BROWSER        │
                 │ HTML + CSS + JS      │
                 └──────────┬───────────┘
                            │
                         Import
                            │
                            ▼
                 POST /api/upload
                            │
                            ▼
                 ┌──────────────────────┐
                 │       FastAPI        │
                 │       main.py        │
                 └──────────┬───────────┘
                            │
                     Save Original
                      Image + UUID
                            │
                            ▼
                 Frontend receives
                      image_id
                            │
                      Slider Change
                            │
                            ▼
                 POST /api/process
                            │
                            ▼
              ┌─────────────┴─────────────┐
              │                           │
           HSV selected             Histogram selected
              │                           │
              ▼                           ▼
    algorithms/hsv.py        algorithms/histogram.py
              │                           │
              └─────────────┬─────────────┘
                            │
                         OpenCV
                            │
                            ▼
                     JPEG Preview
                            │
                            ▼
                       Browser
                            │
                            ▼
                     OUTPUT IMAGE
```

---

# 📤 Export Flow

```text
Browser
   │
   │ POST /api/export
   ▼
FastAPI
   │
   ├── Load Original Image
   │
   ├── Read Current Settings
   │
   ├── Apply Selected Algorithm
   │
   └── Process Full Resolution
            │
            ▼
          PNG
            │
            ▼
         Download
```

---

# 🚀 Installation

## 1. Clone / Download project

Di chuyển vào thư mục:

```bash
cd cyberpunk_image_lab
```

---

## 2. Tạo Virtual Environment

```bash
python -m venv .venv
```

### Windows

```bash
.venv\Scripts\activate
```

---

## 3. Cài dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Chạy FastAPI Server

```bash
uvicorn main:app --reload --port 5500
```

Nếu server chạy thành công:

```text
Uvicorn running on http://127.0.0.1:5500
```

---

## 5. Mở Web Application

Truy cập:

```text
http://127.0.0.1:5500
```

---

# 🔌 API

## Upload Image

```http
POST /api/upload
```

Chức năng:

```text
Image
 ↓
Server
 ↓
UUID
 ↓
image_id
```

---

## Process Image

```http
POST /api/process
```

Ví dụ dữ liệu HSV:

```json
{
    "image_id": "xxxxxxxx",
    "technique": "hsv",
    "parameters": {
        "hue": 20,
        "saturation": 30,
        "value": 10
    }
}
```

Histogram:

```json
{
    "image_id": "xxxxxxxx",
    "technique": "histogram",
    "parameters": {
        "blacks": -10,
        "shadows": 15,
        "midtones": 20,
        "highlights": -5,
        "whites": 10
    }
}
```

---

## Export Image

```http
POST /api/export
```

Backend sử dụng ảnh gốc full-resolution và áp dụng lại các thông số hiện tại trước khi export.

---

# 🛠️ Technology Stack

### Backend

```text
Python
FastAPI
OpenCV
NumPy
```

### Frontend

```text
HTML5
CSS3
Vanilla JavaScript
Canvas API
```

### Image Processing

```text
HSV Color Space
LAB Color Space
Luminance Processing
Gaussian Tonal Weighting
Histogram Analysis
```

---

# 🎯 Main Pipeline

```text
IMPORT IMAGE
      ↓
LOAD ORIGINAL IMAGE
      ↓
SELECT TECHNIQUE
      ↓
┌───────────────┬──────────────────┐
│      HSV      │    HISTOGRAM     │
├───────────────┼──────────────────┤
│ Hue           │ Blacks           │
│ Saturation    │ Shadows          │
│ Value         │ Midtones         │
│               │ Highlights       │
│               │ Whites           │
└───────┬───────┴─────────┬────────┘
        │                 │
        └────────┬────────┘
                 ↓
              OpenCV
                 ↓
         REALTIME PREVIEW
                 ↓
           RESET / EXPORT
                 ↓
        FULL RESOLUTION PNG
```

---

# 🌌 NEON // IMAGE LAB

```text
IMAGE
  ×
CODE
  ×
CYBERPUNK
```

> Local processing.
> Realtime control.
> Simple image manipulation with Python & OpenCV.
