"""
Script Test API - Hệ thống AI Đọc Báo Cáo VTC NETVIET
Chạy: python test_api.py
"""

import requests
import json
import time
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

BASE_URL = "http://localhost:8502"

def print_section(title):
    """In tiêu đề section"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_health():
    """Test 1: Health check"""
    print_section("TEST 1: HEALTH CHECK")

    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"✅ Service: {data['service']}")
            print(f"✅ Version: {data['version']}")
            return True
        else:
            print(f"❌ Lỗi: Status code {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Không thể kết nối server: {e}")
        print("⚠️  Đảm bảo server đang chạy: python api_service.py")
        return False

def test_analyze_text():
    """Test 2: Phân tích văn bản"""
    print_section("TEST 2: PHÂN TÍCH VĂN BẢN")

    sample_text = """
    BÁO CÁO KẾT QUẢ KINH DOANH QUÝ 3/2024
    CÔNG TY VTC NETVIET
    
    I. TỔNG QUAN
    Quý 3/2024 ghi nhận doanh thu đạt 138 tỷ đồng, giảm 5% so với quý trước
    nhưng vẫn tăng 18% so với cùng kỳ năm ngoái.
    
    II. CÁC CHỈ SỐ CHÍNH
    - Doanh thu: 138 tỷ đồng (-5% QoQ, +18% YoY)
    - Chi phí hoạt động: 105 tỷ đồng
    - EBITDA: 33 tỷ đồng (+10% YoY)
    - Lợi nhuận sau thuế: 19 tỷ đồng (-14% QoQ, +26% YoY)
    - Khách hàng mới: 1,380 khách hàng (-5% QoQ)
    
    III. PHÂN TÍCH
    Sự sụt giảm nhẹ do yếu tố mùa vụ và điều chỉnh chiến lược sản phẩm.
    Mảng AI và Cloud duy trì tăng trưởng mạnh với 65% tổng doanh thu.
    """

    analysis_types = ["summary", "detailed", "insights"]

    for analysis_type in analysis_types:
        print(f"\n📊 Đang test phân tích loại: {analysis_type.upper()}")

        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/api/analyze/text",
                json={
                    "text": sample_text,
                    "analysis_type": analysis_type
                }
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Thành công - Thời gian: {elapsed:.2f}s")
                print(f"\n📄 Kết quả ({analysis_type}):")
                print("-" * 70)
                print(data["result"][:500] + "..." if len(data["result"]) > 500 else data["result"])
            else:
                print(f"❌ Lỗi: {response.status_code}")

        except Exception as e:
            print(f"❌ Exception: {e}")

def test_create_charts():
    """Test 3: Vẽ các loại biểu đồ"""
    print_section("TEST 3: VẼ BIỂU ĐỒ TỪ DỮ LIỆU")

    # Tạo thư mục output
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    charts = {
        "line_chart": {
            "data": {
                "x": ["Q1", "Q2", "Q3", "Q4"],
                "y": [100, 120, 115, 140],
                "label": "Doanh thu (tỷ VNĐ)"
            },
            "chart_type": "line",
            "title": "Doanh thu theo quý 2024",
            "xlabel": "Quý",
            "ylabel": "Doanh thu (tỷ)"
        },
        "bar_chart": {
            "data": {
                "x": ["Sản phẩm A", "Sản phẩm B", "Sản phẩm C", "Sản phẩm D"],
                "y": [45, 60, 38, 52]
            },
            "chart_type": "bar",
            "title": "So sánh doanh số sản phẩm",
            "xlabel": "Sản phẩm",
            "ylabel": "Doanh số"
        },
        "pie_chart": {
            "data": {
                "labels": ["VTC NETVIET", "Đối thủ A", "Đối thủ B", "Khác"],
                "values": [35, 25, 20, 20]
            },
            "chart_type": "pie",
            "title": "Thị phần thị trường 2024"
        },
        "scatter_chart": {
            "data": {
                "x": [10, 20, 30, 40, 50, 60, 70, 80],
                "y": [15, 25, 20, 35, 45, 40, 55, 60],
                "sizes": [50, 100, 150, 200, 250, 150, 100, 300]
            },
            "chart_type": "scatter",
            "title": "Mối quan hệ chi phí marketing - doanh thu",
            "xlabel": "Chi phí marketing (triệu)",
            "ylabel": "Doanh thu (tỷ)"
        },
        "heatmap": {
            "data": {
                "matrix": [
                    [85, 92, 78, 88],
                    [90, 95, 82, 91],
                    [78, 85, 88, 94]
                ],
                "xlabels": ["Q1", "Q2", "Q3", "Q4"],
                "ylabels": ["Miền Bắc", "Miền Trung", "Miền Nam"]
            },
            "chart_type": "heatmap",
            "title": "Hiệu suất theo khu vực & quý (điểm)"
        }
    }

    for chart_name, chart_config in charts.items():
        print(f"\n📊 Đang tạo: {chart_name}")

        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/api/chart/create",
                json=chart_config
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                filename = output_dir / f"{chart_name}.png"
                with open(filename, "wb") as f:
                    f.write(response.content)
                print(f"✅ Đã tạo: {filename} - Thời gian: {elapsed:.2f}s")
            else:
                print(f"❌ Lỗi: {response.status_code}")

        except Exception as e:
            print(f"❌ Exception: {e}")

    print(f"\n📁 Tất cả biểu đồ đã được lưu vào thư mục: {output_dir}")

def test_smart_chart():
    """Test 4: Tạo biểu đồ thông minh"""
    print_section("TEST 4: TẠO BIỂU ĐỒ THÔNG MINH TỪ MÔ TẢ")

    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    test_cases = [
        {
            "name": "smart_bar_chart",
            "description": "Vẽ biểu đồ cột so sánh doanh thu 4 quý: Q1 là 100 tỷ, Q2 là 120 tỷ, Q3 là 115 tỷ, Q4 là 140 tỷ"
        },
        {
            "name": "smart_pie_chart",
            "description": "Tạo biểu đồ tròn thị phần: VTC NETVIET chiếm 35%, Đối thủ A 25%, Đối thủ B 20%, và phần còn lại là 20%"
        },
        {
            "name": "smart_line_chart",
            "description": "Vẽ đường xu hướng tăng trưởng doanh thu từ 2020 đến 2024: năm 2020 là 50 tỷ, 2021 là 65 tỷ, 2022 là 80 tỷ, 2023 là 95 tỷ, 2024 là 110 tỷ"
        }
    ]

    for test_case in test_cases:
        print(f"\n🤖 Test case: {test_case['name']}")
        print(f"📝 Mô tả: {test_case['description']}")

        try:
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/api/chart/smart",
                json={
                    "text_description": test_case["description"],
                    "report_context": "Báo cáo tài chính VTC NETVIET"
                }
            )
            elapsed = time.time() - start_time

            if response.status_code == 200:
                filename = output_dir / f"{test_case['name']}.png"
                with open(filename, "wb") as f:
                    f.write(response.content)

                # Lấy config từ header nếu có
                config = response.headers.get('X-Chart-Config', 'N/A')

                print(f"✅ Đã tạo: {filename} - Thời gian: {elapsed:.2f}s")
                if config != 'N/A':
                    print(f"⚙️  Config: {config[:100]}...")
            else:
                print(f"❌ Lỗi: {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ Exception: {e}")

def test_compare_reports():
    """Test 5: So sánh báo cáo"""
    print_section("TEST 5: SO SÁNH NHIỀU BÁO CÁO")

    reports = [
        {
            "period": "Q1/2024",
            "content": """
            Doanh thu: 125 tỷ đồng
            Lợi nhuận: 18 tỷ đồng
            Khách hàng mới: 1,250
            Tỷ lệ tăng trưởng: +23% YoY
            Mảng Cloud: 60% doanh thu
            """
        },
        {
            "period": "Q2/2024",
            "content": """
            Doanh thu: 145 tỷ đồng (+16% QoQ)
            Lợi nhuận: 22 tỷ đồng (+22% QoQ)
            Khách hàng mới: 1,450 (+16% QoQ)
            Tỷ lệ tăng trưởng: +28% YoY
            Mảng Cloud: 62% doanh thu
            """
        },
        {
            "period": "Q3/2024",
            "content": """
            Doanh thu: 138 tỷ đồng (-5% QoQ, +18% YoY)
            Lợi nhuận: 19 tỷ đồng (-14% QoQ, +26% YoY)
            Khách hàng mới: 1,380 (-5% QoQ)
            Tỷ lệ tăng trưởng: +18% YoY
            Mảng Cloud: 65% doanh thu
            """
        }
    ]

    try:
        print("\n📊 Đang so sánh 3 quý báo cáo...")
        start_time = time.time()

        response = requests.post(
            f"{BASE_URL}/api/reports/compare",
            json={"reports": reports}
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Thành công - Thời gian: {elapsed:.2f}s")
            print(f"\n📄 Kết quả so sánh:")
            print("-" * 70)
            print(data["comparison"])
        else:
            print(f"❌ Lỗi: {response.status_code}")

    except Exception as e:
        print(f"❌ Exception: {e}")

def test_demo_endpoints():
    """Test 6: Demo endpoints"""
    print_section("TEST 6: DEMO ENDPOINTS")

    # Test chart examples
    print("\n📊 Lấy ví dụ biểu đồ...")
    try:
        response = requests.get(f"{BASE_URL}/api/demo/chart-examples")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Có {len(data['examples'])} loại biểu đồ mẫu:")
            for chart_name in data["examples"].keys():
                print(f"   - {chart_name}")
        else:
            print(f"❌ Lỗi: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

    # Test analysis examples
    print("\n📄 Lấy ví dụ phân tích...")
    try:
        response = requests.get(f"{BASE_URL}/api/demo/analysis-examples")
        if response.status_code == 200:
            data = response.json()
            print("✅ Có các loại phân tích:")
            for key in data.keys():
                print(f"   - {key}")
        else:
            print(f"❌ Lỗi: {response.status_code}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def create_sample_image_for_test():
    """Tạo ảnh mẫu để test OCR"""
    print_section("TẠO ẢNH MẪU ĐỂ TEST")

    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)

    # Tạo biểu đồ mẫu
    fig, ax = plt.subplots(figsize=(10, 6))

    categories = ['Q1', 'Q2', 'Q3', 'Q4']
    values = [100, 120, 115, 140]

    ax.bar(categories, values, color=['#667eea', '#764ba2', '#f093fb', '#4facfe'])
    ax.set_title('Doanh thu theo quý 2024', fontsize=16, fontweight='bold')
    ax.set_xlabel('Quý', fontsize=12)
    ax.set_ylabel('Doanh thu (tỷ VNĐ)', fontsize=12)
    ax.grid(axis='y', alpha=0.3)

    # Thêm giá trị lên cột
    for i, v in enumerate(values):
        ax.text(i, v + 2, str(v), ha='center', fontsize=11, fontweight='bold')

    filename = output_dir / "sample_chart_for_ocr.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✅ Đã tạo ảnh mẫu: {filename}")
    return filename

def test_analyze_image():
    """Test 7: Phân tích ảnh"""
    print_section("TEST 7: PHÂN TÍCH ẢNH/BIỂU ĐỒ")

    # Tạo ảnh mẫu
    image_path = create_sample_image_for_test()

    prompt_types = ["chart", "data", "general"]

    for prompt_type in prompt_types:
        print(f"\n📸 Test phân tích ảnh với prompt_type: {prompt_type}")

        try:
            start_time = time.time()

            with open(image_path, "rb") as f:
                files = {"file": f}
                params = {"prompt_type": prompt_type}

                response = requests.post(
                    f"{BASE_URL}/api/analyze/image",
                    files=files,
                    params=params
                )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Thành công - Thời gian: {elapsed:.2f}s")
                print(f"\n📄 Kết quả phân tích ({prompt_type}):")
                print("-" * 70)
                print(data["analysis"][:400] + "..." if len(data["analysis"]) > 400 else data["analysis"])
            else:
                print(f"❌ Lỗi: {response.status_code}")

        except Exception as e:
            print(f"❌ Exception: {e}")

def run_all_tests():
    """Chạy tất cả test"""
    print("\n" + "🚀" * 35)
    print("  BẮT ĐẦU TEST API - HỆ THỐNG AI ĐỌC BÁO CÁO VTC NETVIET")
    print("🚀" * 35)

    start_time = time.time()

    # Kiểm tra server trước
    if not test_health():
        print("\n⛔ Server không hoạt động. Vui lòng khởi động server trước:")
        print("   python api_service.py")
        return

    # Chạy các test
    test_analyze_text()
    test_create_charts()
    test_smart_chart()
    test_compare_reports()
    test_analyze_image()
    test_demo_endpoints()

    elapsed = time.time() - start_time

    print("\n" + "✅" * 35)
    print(f"  HOÀN THÀNH TẤT CẢ TEST - Tổng thời gian: {elapsed:.2f}s")
    print("✅" * 35)
    print(f"\n📁 Kết quả đã lưu vào thư mục: test_output/")
    print(f"📊 Xem các biểu đồ đã tạo trong thư mục test_output/")

if __name__ == "__main__":
    run_all_tests()