"""
Module: Smart Chart Generator
Tự động trích xuất dữ liệu và tạo biểu đồ từ báo cáo tài chính
"""

import json
import re
from typing import Dict, List, Any, Optional
from openai import OpenAI

client = OpenAI()


class SmartChartGenerator:
    """
    Class xử lý thông minh để tạo biểu đồ từ báo cáo tài chính
    """

    EXTRACTION_PROMPT = """Bạn là chuyên gia phân tích báo cáo tài chính và data visualization.

NHIỆM VỤ: Trích xuất TẤT CẢ dữ liệu số từ báo cáo tài chính và đề xuất các biểu đồ phù hợp.

QUY TẮC QUAN TRỌNG:
1. Tìm tất cả các bảng số liệu, chỉ số tài chính
2. Trích xuất số liệu CHÍNH XÁC (giữ nguyên đơn vị: triệu, tỷ, %, v.v.)
3. Nhóm dữ liệu theo loại: doanh thu, lợi nhuận, tài sản, nợ, tỷ lệ...
4. Đề xuất 3-5 biểu đồ quan trọng nhất

ĐỊNH DẠNG OUTPUT (JSON):
{
    "extracted_data": {
        "revenue": {
            "periods": ["Q1 2024", "Q2 2024", ...],
            "values": [100, 120, ...],
            "unit": "tỷ VNĐ"
        },
        "profit": {...},
        "assets": {...},
        "liabilities": {...}
    },
    "recommended_charts": [
        {
            "title": "Tên biểu đồ",
            "type": "line|bar|pie|area|scatter",
            "data_source": "revenue|profit|assets|...",
            "priority": 1,
            "description": "Giải thích tại sao cần biểu đồ này"
        }
    ]
}

BÁO CÁO TÀI CHÍNH:
{report_content}
"""

    CHART_GENERATION_PROMPT = """Bạn là chuyên gia tạo biểu đồ từ dữ liệu tài chính.

NHIỆM VỤ: Tạo cấu hình biểu đồ CHÍNH XÁC để vẽ ngay lập tức.

DỮ LIỆU ĐÃ TRÍCH XUẤT:
{extracted_data}

YÊU CẦU BIỂU ĐỒ: {chart_request}

ĐỊNH DẠNG OUTPUT (JSON - KHÔNG THÊM TEXT):
{
    "chart_type": "line|bar|pie|area|scatter|heatmap",
    "title": "Tiêu đề biểu đồ cụ thể",
    "xlabel": "Nhãn trục X (nếu có)",
    "ylabel": "Nhãn trục Y (nếu có)", 
    "data": {
        // Dữ liệu chính xác theo format của chart_type:
        // line/bar/area: {"x": [...], "y": [...], "label": "..."}
        // pie: {"labels": [...], "values": [...]}
        // scatter: {"x": [...], "y": [...], "sizes": [...]}
    }
}

LƯU Ý: Số liệu phải CHÍNH XÁC từ dữ liệu đã trích xuất!
"""

    def __init__(self, api_key: str = None):
        """Khởi tạo với OpenAI API key"""
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = client

    def extract_financial_data(self, report_content: str) -> Dict[str, Any]:
        """
        Bước 1: Trích xuất dữ liệu tài chính từ báo cáo

        Returns:
            Dict chứa extracted_data và recommended_charts
        """
        prompt = self.EXTRACTION_PROMPT.format(report_content=report_content)

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia phân tích tài chính. Trả về ĐÚNG format JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )

        result = response.choices[0].message.content.strip()

        # Parse JSON (xử lý markdown code block)
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI không trả về JSON hợp lệ: {result[:200]}")

    def generate_chart_config(
            self,
            extracted_data: Dict[str, Any],
            chart_request: str = "Tạo biểu đồ quan trọng nhất"
    ) -> Dict[str, Any]:
        """
        Bước 2: Tạo cấu hình biểu đồ từ dữ liệu đã trích xuất

        Args:
            extracted_data: Dữ liệu từ extract_financial_data()
            chart_request: Yêu cầu cụ thể (hoặc dùng recommended_charts)

        Returns:
            Dict cấu hình biểu đồ sẵn sàng vẽ
        """
        prompt = self.CHART_GENERATION_PROMPT.format(
            extracted_data=json.dumps(extracted_data, ensure_ascii=False, indent=2),
            chart_request=chart_request
        )

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Bạn là chuyên gia data visualization. Trả về ĐÚNG format JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )

        result = response.choices[0].message.content.strip()

        # Parse JSON
        if result.startswith("```"):
            result = result.split("```")[1]
            if result.startswith("json"):
                result = result[4:]
        result = result.strip()

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            raise ValueError(f"Không thể parse cấu hình biểu đồ: {result[:200]}")

    def generate_multiple_charts(
            self,
            report_content: str,
            num_charts: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Pipeline hoàn chỉnh: Trích xuất dữ liệu + Tạo nhiều biểu đồ

        Args:
            report_content: Nội dung báo cáo tài chính
            num_charts: Số lượng biểu đồ cần tạo

        Returns:
            List các cấu hình biểu đồ sẵn sàng vẽ
        """
        # Bước 1: Trích xuất dữ liệu
        print("🔍 Đang trích xuất dữ liệu tài chính...")
        extraction_result = self.extract_financial_data(report_content)

        extracted_data = extraction_result.get("extracted_data", {})
        recommended_charts = extraction_result.get("recommended_charts", [])

        if not extracted_data:
            raise ValueError("Không thể trích xuất dữ liệu từ báo cáo")

        print(f"✅ Đã trích xuất {len(extracted_data)} nhóm dữ liệu")
        print(f"📊 Đề xuất {len(recommended_charts)} biểu đồ")

        # Bước 2: Tạo biểu đồ theo đề xuất
        chart_configs = []

        for i, chart_rec in enumerate(recommended_charts[:num_charts]):
            print(f"\n📈 Đang tạo biểu đồ {i + 1}/{num_charts}: {chart_rec['title']}")

            try:
                chart_config = self.generate_chart_config(
                    extracted_data=extracted_data,
                    chart_request=f"Tạo {chart_rec['type']} chart: {chart_rec['title']}"
                )

                # Thêm metadata
                chart_config["priority"] = chart_rec.get("priority", i + 1)
                chart_config["description"] = chart_rec.get("description", "")

                chart_configs.append(chart_config)
                print(f"✅ Hoàn thành: {chart_config['title']}")

            except Exception as e:
                print(f"⚠️  Lỗi tạo biểu đồ {i + 1}: {e}")
                continue

        return chart_configs


# ==================== INTEGRATION VÀO API ====================

def integrate_smart_chart_to_api(
        pdf_text: str,
        user_request: str = None
) -> Dict[str, Any]:
    """
    Hàm tích hợp vào API endpoint /api/pipeline/full

    Args:
        pdf_text: Text đã trích xuất từ PDF
        user_request: Yêu cầu của user (vd: "Tạo biểu đồ doanh thu")

    Returns:
        Dict chứa extracted_data và chart_configs
    """
    generator = SmartChartGenerator()

    try:
        # Nếu user có yêu cầu cụ thể
        if user_request and any(keyword in user_request.lower()
                                for keyword in ["biểu đồ", "chart", "vẽ", "graph"]):

            print("🎯 Xử lý yêu cầu tạo biểu đồ...")

            # Trích xuất dữ liệu
            extraction_result = generator.extract_financial_data(pdf_text)
            extracted_data = extraction_result.get("extracted_data", {})

            # Tạo biểu đồ theo yêu cầu
            chart_config = generator.generate_chart_config(
                extracted_data=extracted_data,
                chart_request=user_request
            )

            return {
                "extracted_data": extracted_data,
                "chart_configs": [chart_config],
                "recommended_charts": extraction_result.get("recommended_charts", [])
            }

        else:
            # Tạo nhiều biểu đồ mặc định
            chart_configs = generator.generate_multiple_charts(
                report_content=pdf_text,
                num_charts=3
            )

            return {
                "chart_configs": chart_configs
            }

    except Exception as e:
        return {
            "error": str(e),
            "extracted_data": None,
            "chart_configs": []
        }


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    # Test với dữ liệu mẫu
    sample_report = """
    BÁO CÁO TÀI CHÍNH Q1 2024-2025

    DOANH THU VÀ LỢI NHUẬN:
    - Q1 2024: Doanh thu 125 tỷ VNĐ, Lợi nhuận 18 tỷ VNĐ
    - Q2 2024: Doanh thu 145 tỷ VNĐ, Lợi nhuận 22 tỷ VNĐ  
    - Q3 2024: Doanh thu 138 tỷ VNĐ, Lợi nhuận 19 tỷ VNĐ
    - Q4 2024: Doanh thu 160 tỷ VNĐ, Lợi nhuận 25 tỷ VNĐ

    TÀI SẢN VÀ NỢ PHẢI TRẢ (31/12/2024):
    - Tổng tài sản: 850 tỷ VNĐ
    - Nợ ngắn hạn: 180 tỷ VNĐ
    - Nợ dài hạn: 220 tỷ VNĐ
    - Vốn chủ sở hữu: 450 tỷ VNĐ

    CƠ CẤU DOANH THU:
    - Cloud Services: 45%
    - AI Solutions: 30%
    - Consulting: 15%
    - Others: 10%
    """

    generator = SmartChartGenerator()

    print("=" * 70)
    print("DEMO: SMART CHART GENERATOR")
    print("=" * 70)

    # Test 1: Tạo nhiều biểu đồ
    print("\n📊 TEST 1: Tạo 3 biểu đồ từ báo cáo")
    chart_configs = generator.generate_multiple_charts(sample_report, num_charts=3)

    print(f"\n✅ Đã tạo {len(chart_configs)} biểu đồ:")
    for i, config in enumerate(chart_configs, 1):
        print(f"\n{i}. {config['title']}")
        print(f"   Loại: {config['chart_type']}")
        print(f"   Mô tả: {config.get('description', 'N/A')}")

    # Test 2: Tạo biểu đồ theo yêu cầu cụ thể
    print("\n" + "=" * 70)
    print("📊 TEST 2: Tạo biểu đồ theo yêu cầu cụ thể")

    result = integrate_smart_chart_to_api(
        pdf_text=sample_report,
        user_request="Vẽ biểu đồ cột so sánh doanh thu 4 quý"
    )

    if result.get("chart_configs"):
        config = result["chart_configs"][0]
        print(f"\n✅ Đã tạo: {config['title']}")
        print(f"   Data: {json.dumps(config['data'], ensure_ascii=False, indent=2)}")