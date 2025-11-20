# 🧪 Hướng dẫn Test API - Fix Lỗi

## ❌ Lỗi bạn gặp phải

Lỗi: `"Input should be a valid list"` cho trường `image_files`

**Nguyên nhân:** API endpoint định nghĩa `image_files` là list nhưng form-data chỉ gửi 1 file.

## ✅ Giải pháp

Đã fix trong code API. Giờ có thể gửi:
- **1 file**: OK
- **Nhiều file**: OK  
- **Không có file**: OK (empty list)

---

## 🚀 Cách Test với Postman

### Test 1: Gửi 1 ảnh + text đơn giản

**Endpoint:** `POST http://localhost:8502/api/pipeline/full`

**Body type:** `form-data`

**Thêm các trường:**

| Key | Type | Value |
|-----|------|-------|
| `image_files` | File | Chọn file ảnh của bạn |
| `text_content` | Text | `Báo cáo trên nói về điều gì` |
| `output_format` | Text | `summary` |

**Click Send** ✅

---

### Test 2: Gửi nhiều ảnh

**Cách 1 - Postman:**
1. Thêm field `image_files` - chọn File
2. Chọn ảnh đầu tiên
3. Click vào `image_files` lần nữa → Chọn ảnh thứ 2
4. Tiếp tục cho các ảnh khác
5. Thêm `text_content` và `output_format`
6. Send

**Cách 2 - Chỉnh key thành array:**
- `image_files[]` thay vì `image_files`
- Thêm nhiều field `image_files[]`, mỗi field 1 ảnh

---

## 📝 Test với cURL

### Test cơ bản - 1 ảnh + text

```bash
curl -X POST "http://localhost:8502/api/pipeline/full" \
  -F "image_files=@/path/to/your/image.png" \
  -F "text_content=Phân tích nội dung trong ảnh này" \
  -F "output_format=summary"
```

### Test với nhiều ảnh

```bash
curl -X POST "http://localhost:8502/api/pipeline/full" \
  -F "image_files=@image1.png" \
  -F "image_files=@image2.png" \
  -F "image_files=@image3.png" \
  -F "text_content=So sánh 3 biểu đồ" \
  -F "output_format=detailed"
```

### Test với PDF + ảnh + text

```bash
curl -X POST "http://localhost:8502/api/pipeline/full" \
  -F "pdf_file=@report.pdf" \
  -F "image_files=@chart1.png" \
  -F "image_files=@chart2.png" \
  -F "text_content=Ghi chú bổ sung" \
  -F "output_format=json" \
  -o result.json
```

---

## 🐍 Test với Python

### Script đơn giản nhất

```python
import requests

# Chuẩn bị file
files = [
    ('image_files', open('screenshot.png', 'rb'))
]

data = {
    'text_content': 'Báo cáo trên nói về điều gì',
    'output_format': 'summary'
}

# Gửi request
response = requests.post(
    'http://localhost:8502/api/pipeline/full',
    files=files,
    data=data
)

# Xem kết quả
if response.status_code == 200:
    result = response.json()
    print("Kết quả phân tích:")
    print(result['analysis']['result'])
else:
    print(f"Lỗi: {response.status_code}")
    print(response.text)
```

### Script với nhiều ảnh

```python
import requests
from pathlib import Path

# Đường dẫn các ảnh
image_paths = [
    'screenshot1.png',
    'screenshot2.png', 
    'chart.png'
]

# Mở tất cả file
files = []
file_objects = []

for img_path in image_paths:
    f = open(img_path, 'rb')
    file_objects.append(f)
    files.append(('image_files', (Path(img_path).name, f, 'image/png')))

# Data
data = {
    'text_content': '''
    YÊU CẦU:
    1. Đọc tất cả ảnh
    2. Trích xuất số liệu
    3. Tóm tắt nội dung
    ''',
    'output_format': 'detailed'
}

# Gửi request
try:
    response = requests.post(
        'http://localhost:8502/api/pipeline/full',
        files=files,
        data=data
    )
    
    if response.status_code == 200:
        result = response.json()
        
        # In kết quả OCR từng ảnh
        print("=== KẾT QUẢ OCR ===")
        for img in result.get('ocr_results', {}).get('images', []):
            print(f"\n📸 {img['filename']}:")
            print(img['analysis'][:300] + "...")
        
        # In phân tích tổng hợp
        print("\n=== PHÂN TÍCH TỔNG HỢP ===")
        print(result['analysis']['result'])
        
        # Lưu vào file
        with open('result.txt', 'w', encoding='utf-8') as f:
            f.write(result['analysis']['result'])
        print("\n✅ Đã lưu vào result.txt")
        
    else:
        print(f"❌ Lỗi {response.status_code}: {response.text}")
        
finally:
    # Đóng tất cả file
    for f in file_objects:
        f.close()
```

---

## 🎯 Test Case Cụ Thể cho Screenshot của bạn

Dựa trên screenshot bạn gửi:

```python
import requests

# File ảnh của bạn
image_file = 'Screenshot from 2025-11-20 11-58-08.png'

files = [
    ('image_files', open(image_file, 'rb'))
]

data = {
    'text_content': 'Báo cáo trên nói về điều gì',
    'output_format': 'summary'
}

response = requests.post(
    'http://localhost:8502/api/pipeline/full',
    files=files,
    data=data
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print("\n✅ Thành công!")
    print("\nPhân tích:")
    print(result['analysis']['result'])
else:
    print(f"\n❌ Lỗi: {response.text}")
```

---

## 🔧 Troubleshooting

### Lỗi "Input should be a valid list"

**Giải pháp:**
1. Khởi động lại server với code đã fix
2. Đảm bảo dùng đúng field name: `image_files` (không phải `image_file`)
3. Với Postman: Đảm bảo Type là "File" không phải "Text"

### Server không chạy

```bash
# Check xem port 8502 có đang dùng không
lsof -i :8502

# Kill process nếu cần
kill -9 <PID>

# Khởi động lại
python api_service.py
```

### Module không tìm thấy

```bash
pip install fastapi uvicorn openai PyPDF2 Pillow matplotlib pandas numpy python-multipart
```

---

## 📊 Output mẫu

Khi test thành công, bạn sẽ nhận được JSON như này:

```json
{
  "input_summary": {},
  "ocr_results": {
    "images": [
      {
        "filename": "Screenshot from 2025-11-20 11-58-08.png",
        "analysis": "Ảnh này là giao diện Postman đang cấu hình test API..."
      }
    ]
  },
  "analysis": {
    "output_format": "summary",
    "result": "# TÓM TẮT\n\nẢnh cho thấy đang test API với form-data..."
  },
  "statistics": {
    "total_tokens_used": 1234,
    "pdf_processed": false,
    "images_processed": 1,
    "output_format": "summary"
  },
  "timestamp": "2024-11-20T12:00:00"
}
```

---

## 💡 Tips

1. **Với ảnh lớn:** Nén xuống dưới 5MB trước khi gửi
2. **Text dài:** Nếu text_content > 5000 từ, nên chia nhỏ
3. **Nhiều ảnh:** Gửi tối đa 10 ảnh/request để tránh timeout
4. **Output format:**
   - `summary` - Nhanh nhất, tóm tắt ngắn
   - `detailed` - Chi tiết nhất
   - `insights` - Phát hiện insight
   - `json` - Dữ liệu có cấu trúc

---

## ✅ Checklist Test

- [ ] Server đang chạy trên port 8502
- [ ] Truy cập http://localhost:8502/docs được
- [ ] API key OpenAI đã cấu hình
- [ ] File ảnh tồn tại và < 5MB
- [ ] Field name đúng: `image_files` (có 's')
- [ ] Type của field là File trong Postman
- [ ] Đã restart server sau khi fix code

---

## 🆘 Cần trợ giúp?

Nếu vẫn gặp lỗi, hãy gửi cho tôi:
1. Screenshot Postman/code bạn dùng
2. Full error message
3. Log từ server (terminal chạy api_service.py)