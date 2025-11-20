"""
API Service - Hệ thống AI Đọc Báo Cáo & Vẽ Biểu Đồ
VTC NETVIET - FULL VERSION WITH SMART CHART GENERATOR

Chạy server: python api_service.py
Hoặc: uvicorn api_service:app --host 0.0.0.0 --port 8502 --reload
Truy cập docs: http://localhost:8502/docs
"""

import os
import base64
import json
import io
import zipfile
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query, Body
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import matplotlib
matplotlib.use('Agg')  # Backend không cần GUI
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from openai import OpenAI
import PyPDF2
from PIL import Image

# Import Smart Chart Generator
from smart_chart_generator import SmartChartGenerator, integrate_smart_chart_to_api

# Cấu hình
os.environ["OPENAI_API_KEY"] = os.getenv(
    "OPENAI_API_KEY",
    ""  # Thay bằng key của bạn hoặc set environment variable
)
client = OpenAI()

# Khởi tạo FastAPI
app = FastAPI(
    title="API Hệ thống AI Đọc Báo Cáo - VTC NETVIET",
    description="API để phân tích báo cáo, vẽ biểu đồ và trích xuất thông tin từ tài liệu",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== MODELS ====================

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., description="Nội dung văn bản báo cáo")
    analysis_type: str = Field(
        "summary",
        description="Loại phân tích: summary, detailed, insights, qa, json"
    )

class ChartRequest(BaseModel):
    data: Dict[str, Any] = Field(..., description="Dữ liệu để vẽ biểu đồ")
    chart_type: str = Field(..., description="Loại biểu đồ: line, bar, pie, scatter, heatmap, area")
    title: str = Field("Biểu đồ", description="Tiêu đề biểu đồ")
    xlabel: Optional[str] = Field(None, description="Nhãn trục X")
    ylabel: Optional[str] = Field(None, description="Nhãn trục Y")
    style: Optional[str] = Field("seaborn", description="Style: default, seaborn, ggplot, bmh")

class SmartChartRequest(BaseModel):
    text_description: str = Field(..., description="Mô tả bằng văn bản về biểu đồ cần vẽ")
    report_context: Optional[str] = Field(None, description="Nội dung báo cáo để AI tự trích xuất dữ liệu")

class CompareReportsRequest(BaseModel):
    reports: List[Dict[str, str]] = Field(..., description="Danh sách báo cáo với period và content")


# ==================== CORE FUNCTIONS ====================

def encode_image_to_base64(image_path: str) -> str:
    """Mã hóa ảnh sang base64"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_text_from_pdf(pdf_file) -> str:
    """Trích xuất text từ PDF"""
    text = ""
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n\n"
    return text

def analyze_with_openai(prompt: str, system_message: str = None) -> str:
    """Gọi OpenAI API"""
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7,
        max_tokens=3000
    )
    return response.choices[0].message.content


def create_chart(data: Dict, chart_type: str, title: str,
                xlabel: str = None, ylabel: str = None, style: str = "seaborn") -> io.BytesIO:
    """
    Tạo biểu đồ từ dữ liệu

    Args:
        data: Dict chứa dữ liệu, ví dụ:
            - line/bar: {"x": [...], "y": [...]}
            - pie: {"labels": [...], "values": [...]}
            - scatter: {"x": [...], "y": [...]}
    """
    plt.style.use(style)
    fig, ax = plt.subplots(figsize=(10, 6))

    # Hỗ trợ tiếng Việt
    plt.rcParams['font.family'] = 'DejaVu Sans'

    try:
        if chart_type == "line":
            x = data.get("x", [])
            y = data.get("y", [])
            label = data.get("label", "")
            ax.plot(x, y, marker='o', linewidth=2, markersize=8, label=label)
            ax.grid(True, alpha=0.3)
            if label:
                ax.legend()

        elif chart_type == "bar":
            x = data.get("x", [])
            y = data.get("y", [])
            colors = data.get("colors", plt.cm.Set3(range(len(x))))
            ax.bar(x, y, color=colors, alpha=0.8, edgecolor='black')
            ax.grid(axis='y', alpha=0.3)

        elif chart_type == "pie":
            labels = data.get("labels", [])
            values = data.get("values", [])
            colors = data.get("colors", plt.cm.Set3(range(len(labels))))
            explode = data.get("explode", [0.05] * len(labels))
            ax.pie(values, labels=labels, autopct='%1.1f%%',
                   colors=colors, explode=explode, shadow=True, startangle=90)
            ax.axis('equal')

        elif chart_type == "scatter":
            x = data.get("x", [])
            y = data.get("y", [])
            sizes = data.get("sizes", [100] * len(x))
            colors = data.get("colors", range(len(x)))
            scatter = ax.scatter(x, y, s=sizes, c=colors, alpha=0.6,
                                cmap='viridis', edgecolors='black', linewidth=1)
            plt.colorbar(scatter, ax=ax)
            ax.grid(True, alpha=0.3)

        elif chart_type == "heatmap":
            matrix = data.get("matrix", [[]])
            xlabels = data.get("xlabels", [])
            ylabels = data.get("ylabels", [])
            im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto')

            if xlabels:
                ax.set_xticks(range(len(xlabels)))
                ax.set_xticklabels(xlabels, rotation=45, ha='right')
            if ylabels:
                ax.set_yticks(range(len(ylabels)))
                ax.set_yticklabels(ylabels)

            plt.colorbar(im, ax=ax)

            # Thêm giá trị vào ô
            for i in range(len(matrix)):
                for j in range(len(matrix[0])):
                    text = ax.text(j, i, f'{matrix[i][j]:.1f}',
                                 ha="center", va="center", color="black", fontsize=9)

        elif chart_type == "area":
            x = data.get("x", [])
            y = data.get("y", [])
            ax.fill_between(x, y, alpha=0.4)
            ax.plot(x, y, linewidth=2)
            ax.grid(True, alpha=0.3)

        else:
            raise ValueError(f"Loại biểu đồ không hỗ trợ: {chart_type}")

        # Thiết lập tiêu đề và nhãn
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
        if xlabel:
            ax.set_xlabel(xlabel, fontsize=11)
        if ylabel:
            ax.set_ylabel(ylabel, fontsize=11)

        plt.tight_layout()

        # Lưu vào buffer
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        return buffer

    except Exception as e:
        plt.close(fig)
        raise HTTPException(status_code=400, detail=f"Lỗi tạo biểu đồ: {str(e)}")


# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Trang chủ API"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API AI Đọc Báo Cáo - VTC NETVIET</title>
        <style>
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 40px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                background: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                color: #333;
            }
            h1 {
                color: #667eea;
                text-align: center;
                font-size: 2.5em;
                margin-bottom: 10px;
            }
            .subtitle {
                text-align: center;
                color: #666;
                font-size: 1.2em;
                margin-bottom: 40px;
            }
            .version {
                text-align: center;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 10px;
                border-radius: 20px;
                display: inline-block;
                margin: 0 auto 30px auto;
                font-weight: bold;
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 30px 0;
            }
            .feature-card {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 25px;
                border-radius: 15px;
                color: white;
                box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            }
            .feature-card h3 {
                margin-top: 0;
                font-size: 1.3em;
            }
            .feature-card ul {
                margin: 15px 0;
                padding-left: 20px;
            }
            .feature-card.new {
                background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                border: 3px solid #FFD700;
            }
            .button-group {
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-top: 40px;
            }
            .btn {
                padding: 15px 30px;
                border-radius: 10px;
                text-decoration: none;
                font-weight: bold;
                font-size: 1.1em;
                transition: all 0.3s;
                display: inline-block;
            }
            .btn-primary {
                background: #667eea;
                color: white;
            }
            .btn-secondary {
                background: #48bb78;
                color: white;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(0,0,0,0.2);
            }
            .endpoint-list {
                background: #f7fafc;
                padding: 25px;
                border-radius: 15px;
                margin-top: 30px;
            }
            .endpoint-list h3 {
                color: #667eea;
                margin-top: 0;
            }
            .endpoint {
                background: white;
                padding: 15px;
                margin: 10px 0;
                border-radius: 8px;
                border-left: 4px solid #667eea;
            }
            .endpoint.new {
                border-left: 4px solid #f5576c;
                background: #fff5f7;
            }
            .method {
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 10px;
            }
            .method-get { background: #48bb78; color: white; }
            .method-post { background: #4299e1; color: white; }
            .badge {
                background: #FFD700;
                color: #333;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.75em;
                font-weight: bold;
                margin-left: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 API AI Đọc Báo Cáo</h1>
            <div class="subtitle">VTC NETVIET - Hệ thống phân tích báo cáo thông minh</div>
            <div style="text-align: center;">
                <span class="version">⚡ Version 2.0 - Smart Chart Generator</span>
            </div>
            
            <div class="feature-grid">
                <div class="feature-card new">
                    <h3>🆕 Smart Chart Generator</h3>
                    <ul>
                        <li>Tự động trích xuất dữ liệu số</li>
                        <li>AI đề xuất biểu đồ phù hợp</li>
                        <li>Tạo nhiều biểu đồ cùng lúc</li>
                        <li>Xuất PNG hoặc ZIP</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>📊 Vẽ Biểu Đồ Nâng Cao</h3>
                    <ul>
                        <li>Line, Bar, Pie Chart</li>
                        <li>Scatter, Heatmap, Area</li>
                        <li>Tự động tạo từ mô tả văn bản</li>
                        <li>Xuất PNG độ phân giải cao</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>📄 Phân Tích Báo Cáo</h3>
                    <ul>
                        <li>Tóm tắt tự động</li>
                        <li>Phân tích chi tiết</li>
                        <li>Phát hiện insights</li>
                        <li>Hỏi đáp thông minh</li>
                    </ul>
                </div>
                
                <div class="feature-card">
                    <h3>🔍 OCR & Trích Xuất</h3>
                    <ul>
                        <li>Đọc PDF tự động</li>
                        <li>Phân tích ảnh biểu đồ</li>
                        <li>Nhận dạng bảng số liệu</li>
                        <li>So sánh đa kỳ</li>
                    </ul>
                </div>
            </div>
            
            <div class="endpoint-list">
                <h3>📡 API Endpoints</h3>
                
                <div class="endpoint new">
                    <span class="method method-post">POST</span>
                    <strong>/api/pipeline/full</strong> - Pipeline hoàn chỉnh + Smart Charts
                    <span class="badge">NEW</span>
                </div>
                
                <div class="endpoint new">
                    <span class="method method-post">POST</span>
                    <strong>/api/chart/render</strong> - Vẽ biểu đồ từ config
                    <span class="badge">NEW</span>
                </div>
                
                <div class="endpoint new">
                    <span class="method method-post">POST</span>
                    <strong>/api/chart/render-all</strong> - Vẽ tất cả biểu đồ (ZIP)
                    <span class="badge">NEW</span>
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/analyze/text</strong> - Phân tích văn bản
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/analyze/image</strong> - Phân tích ảnh/biểu đồ
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/analyze/pdf</strong> - Phân tích file PDF
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/chart/create</strong> - Vẽ biểu đồ từ dữ liệu
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/chart/smart</strong> - Tạo biểu đồ từ mô tả văn bản
                </div>
                
                <div class="endpoint">
                    <span class="method method-post">POST</span>
                    <strong>/api/reports/compare</strong> - So sánh nhiều báo cáo
                </div>
                
                <div class="endpoint">
                    <span class="method method-get">GET</span>
                    <strong>/api/health</strong> - Kiểm tra trạng thái API
                </div>
            </div>
            
            <div class="button-group">
                <a href="/docs" class="btn btn-primary">📚 Xem API Documentation</a>
                <a href="/redoc" class="btn btn-secondary">📖 Xem ReDoc</a>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/health")
async def health_check():
    """Kiểm tra trạng thái API"""
    return {
        "status": "healthy",
        "service": "AI Report Reader API",
        "version": "2.0.0",
        "features": {
            "smart_chart_generator": True,
            "ocr": True,
            "pdf_analysis": True,
            "multi_chart_export": True
        },
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/analyze/text")
async def analyze_text(request: TextAnalysisRequest):
    """
    Phân tích văn bản báo cáo

    - **text**: Nội dung văn bản cần phân tích
    - **analysis_type**: summary, detailed, insights, qa, json
    """
    try:
        prompts = {
            "summary": "Tóm tắt báo cáo thành Executive Summary với các điểm chính, số liệu quan trọng, xu hướng và khuyến nghị.",
            "detailed": "Phân tích CHI TIẾT báo cáo bao gồm: phân loại, dữ liệu, đánh giá định tính, mối tương quan, kết luận.",
            "insights": "Phát hiện insights sâu sắc: patterns, anomalies, predictive insights, actionable recommendations.",
            "qa": "Tạo 10 câu hỏi quan trọng về báo cáo và trả lời chi tiết từng câu với trích dẫn nguồn.",
            "json": """Trích xuất thông tin thành JSON:
            {
                "report_type": "...",
                "period": "...",
                "key_metrics": [...],
                "summary": "...",
                "trends": [...],
                "recommendations": [...]
            }"""
        }

        prompt = f"{prompts.get(request.analysis_type, prompts['summary'])}\n\nBÁO CÁO:\n{request.text}"
        result = analyze_with_openai(
            prompt,
            "Bạn là chuyên gia phân tích báo cáo của VTC NETVIET, chuyên xử lý báo cáo tiếng Việt."
        )

        return {
            "success": True,
            "analysis_type": request.analysis_type,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
    prompt_type: str = Query("chart", description="Loại phân tích: general, chart, table, data")
):
    """
    Phân tích ảnh/biểu đồ bằng Vision API

    - **file**: File ảnh (PNG, JPG, JPEG)
    - **prompt_type**: chart (biểu đồ), table (bảng), data (số liệu), general (chung)
    """
    try:
        # Đọc file
        contents = await file.read()
        base64_image = base64.b64encode(contents).decode('utf-8')

        prompts = {
            "chart": """Phân tích biểu đồ chi tiết:
            1. Loại biểu đồ và tiêu đề
            2. Các chỉ số và giá trị cụ thể
            3. Xu hướng tăng/giảm
            4. Điểm bất thường
            5. Kết luận và nhận định""",

            "table": """Trích xuất bảng dữ liệu:
            1. Cấu trúc bảng (cột, hàng)
            2. Toàn bộ dữ liệu
            3. Thống kê (max, min, trung bình)
            4. Phân tích và nhận xét""",

            "data": "Trích xuất TẤT CẢ số liệu: giá trị, đơn vị, thời gian, tỷ lệ. Format JSON.",

            "general": "Mô tả chi tiết nội dung trong ảnh, bao gồm text, số liệu, biểu đồ."
        }

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompts.get(prompt_type, prompts["general"])},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=2000
        )

        return {
            "success": True,
            "filename": file.filename,
            "prompt_type": prompt_type,
            "analysis": response.choices[0].message.content,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze/pdf")
async def analyze_pdf(
    file: UploadFile = File(...),
    analysis_type: str = Query("summary", description="Loại phân tích")
):
    """
    Phân tích file PDF

    - **file**: File PDF
    - **analysis_type**: summary, detailed, insights
    """
    try:
        # Trích xuất text
        pdf_file = io.BytesIO(await file.read())
        text = extract_text_from_pdf(pdf_file)

        if not text.strip():
            raise HTTPException(status_code=400, detail="Không thể trích xuất text từ PDF")

        # Phân tích
        prompts = {
            "summary": "Tóm tắt nội dung PDF thành Executive Summary.",
            "detailed": "Phân tích chi tiết toàn bộ nội dung PDF.",
            "insights": "Phát hiện insights và khuyến nghị từ PDF."
        }

        result = analyze_with_openai(
            f"{prompts.get(analysis_type, prompts['summary'])}\n\nNỘI DUNG:\n{text}",
            "Bạn là chuyên gia phân tích tài liệu."
        )

        return {
            "success": True,
            "filename": file.filename,
            "text_length": len(text),
            "analysis": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chart/create")
async def create_chart_endpoint(request: ChartRequest):
    """
    Vẽ biểu đồ từ dữ liệu

    **Ví dụ data:**
    - Line/Bar: `{"x": [1,2,3], "y": [10,20,15]}`
    - Pie: `{"labels": ["A","B","C"], "values": [30,50,20]}`
    - Heatmap: `{"matrix": [[1,2],[3,4]], "xlabels": ["X1","X2"], "ylabels": ["Y1","Y2"]}`
    """
    try:
        buffer = create_chart(
            data=request.data,
            chart_type=request.chart_type,
            title=request.title,
            xlabel=request.xlabel,
            ylabel=request.ylabel,
            style=request.style
        )

        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chart/smart")
async def create_smart_chart(request: SmartChartRequest):
    """
    Tạo biểu đồ thông minh từ mô tả văn bản

    AI sẽ tự động:
    1. Hiểu yêu cầu
    2. Trích xuất/tạo dữ liệu
    3. Chọn loại biểu đồ phù hợp
    4. Vẽ biểu đồ

    **Ví dụ:**
    - "Vẽ biểu đồ cột so sánh doanh thu Q1-Q4: 100, 120, 115, 140 tỷ"
    - "Tạo biểu đồ tròn thị phần: VTC 35%, A 25%, B 40%"
    """
    try:
        # Bước 1: AI phân tích yêu cầu và tạo dữ liệu
        analysis_prompt = f"""Phân tích yêu cầu vẽ biểu đồ sau và trả về JSON:

YÊU CẦU: {request.text_description}

NGỮ CẢNH (nếu có): {request.report_context or 'Không có'}

Trả về ĐÚNG format JSON này (không thêm text khác):
{{
    "chart_type": "line|bar|pie|scatter|heatmap|area",
    "title": "Tiêu đề biểu đồ",
    "xlabel": "Nhãn trục X (nếu có)",
    "ylabel": "Nhãn trục Y (nếu có)",
    "data": {{
        // Dữ liệu tương ứng loại biểu đồ
        // Line/Bar: {{"x": [...], "y": [...]}}
        // Pie: {{"labels": [...], "values": [...]}}
        // Heatmap: {{"matrix": [[...]], "xlabels": [...], "ylabels": [...]}}
    }}
}}"""

        ai_response = analyze_with_openai(
            analysis_prompt,
            "Bạn là chuyên gia data visualization. Trả về ĐÚNG format JSON, không thêm text."
        )

        # Parse JSON
        # Xử lý trường hợp AI trả về có markdown
        json_text = ai_response.strip()
        if json_text.startswith("```"):
            json_text = json_text.split("```")[1]
            if json_text.startswith("json"):
                json_text = json_text[4:]
        json_text = json_text.strip()

        chart_config = json.loads(json_text)

        # Bước 2: Vẽ biểu đồ
        buffer = create_chart(
            data=chart_config["data"],
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            xlabel=chart_config.get("xlabel"),
            ylabel=chart_config.get("ylabel"),
            style="seaborn"
        )

        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename=smart_chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                "X-Chart-Config": json.dumps(chart_config, ensure_ascii=False)
            }
        )

    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI response không phải JSON hợp lệ. Response: {ai_response[:200]}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/reports/compare")
async def compare_reports(request: CompareReportsRequest):
    """
    So sánh nhiều báo cáo theo thời gian

    **Input:** List các báo cáo với period và content

    **Output:** Phân tích so sánh chi tiết
    """
    try:
        comparison_prompt = f"""So sánh các báo cáo sau:

{chr(10).join([f"=== {r['period']} ==={chr(10)}{r['content']}{chr(10)}" for r in request.reports])}

Phân tích:
1. Xu hướng chung
2. So sánh cụ thể (bảng + % thay đổi)
3. Nguyên nhân
4. Dự báo"""

        result = analyze_with_openai(
            comparison_prompt,
            "Bạn là chuyên gia phân tích xu hướng và so sánh báo cáo."
        )

        return {
            "success": True,
            "reports_compared": len(request.reports),
            "comparison": result,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== SMART CHART ENDPOINTS ====================

@app.post("/api/pipeline/full")
async def full_pipeline(
    pdf_file: Optional[UploadFile] = File(None),
    image_files: List[UploadFile] = File(default=[]),
    text_content: Optional[str] = Form(None),
    output_format: str = Form("detailed"),
    create_charts: bool = Form(True)
):
    """
    Pipeline xử lý hoàn chỉnh: PDF + Images + Text -> Analysis + Smart Charts

    - **pdf_file**: File PDF (optional)
    - **image_files**: Danh sách file ảnh (optional)
    - **text_content**: Nội dung text hoặc yêu cầu (optional)
    - **output_format**: summary, detailed, insights, json
    - **create_charts**: True = tự động tạo biểu đồ, False = chỉ phân tích
    """
    try:
        results = {
            "input_summary": {},
            "ocr_results": {},
            "analysis": {},
            "charts": {},
            "statistics": {},
            "timestamp": datetime.now().isoformat()
        }

        combined_text = text_content or ""

        # Token counter
        total_tokens = 0

        # 1. Xử lý PDF
        pdf_text = ""
        if pdf_file:
            pdf_content = await pdf_file.read()
            pdf_text = extract_text_from_pdf(io.BytesIO(pdf_content))
            results["input_summary"]["pdf"] = {
                "filename": pdf_file.filename,
                "text_length": len(pdf_text)
            }
            combined_text += f"\n\n=== Từ PDF: {pdf_file.filename} ===\n{pdf_text}"

        # 2. OCR Images
        if image_files:
            results["ocr_results"]["images"] = []

            for img_file in image_files:
                img_content = await img_file.read()
                base64_image = base64.b64encode(img_content).decode('utf-8')

                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Phân tích chi tiết nội dung trong ảnh: biểu đồ, bảng, số liệu, text."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }],
                    max_tokens=1500
                )

                img_analysis = response.choices[0].message.content
                total_tokens += response.usage.total_tokens

                results["ocr_results"]["images"].append({
                    "filename": img_file.filename,
                    "analysis": img_analysis
                })

                combined_text += f"\n\n=== Từ ảnh: {img_file.filename} ===\n{img_analysis}"

        # 3. ==================== SMART CHART GENERATION ====================
        if create_charts and pdf_text:
            print("🎨 Đang tạo biểu đồ thông minh...")

            try:
                chart_result = integrate_smart_chart_to_api(
                    pdf_text=pdf_text,
                    user_request=text_content
                )

                if chart_result.get("chart_configs"):
                    results["charts"]["available"] = True
                    results["charts"]["count"] = len(chart_result["chart_configs"])
                    results["charts"]["configs"] = chart_result["chart_configs"]

                    # Thêm extracted data nếu có
                    if chart_result.get("extracted_data"):
                        results["charts"]["extracted_data"] = chart_result["extracted_data"]

                    # Thêm recommended charts nếu có
                    if chart_result.get("recommended_charts"):
                        results["charts"]["recommendations"] = chart_result["recommended_charts"]

                    print(f"✅ Đã tạo {len(chart_result['chart_configs'])} biểu đồ")
                else:
                    results["charts"]["available"] = False
                    results["charts"]["message"] = "Không thể trích xuất dữ liệu biểu đồ từ báo cáo"

            except Exception as e:
                results["charts"]["available"] = False
                results["charts"]["error"] = str(e)
                print(f"⚠️  Lỗi tạo biểu đồ: {e}")

        # 4. Phân tích tổng hợp
        if combined_text.strip():
            prompts_map = {
                "summary": "Tóm tắt Executive Summary ngắn gọn với các điểm chính",
                "detailed": "Phân tích chi tiết toàn diện báo cáo tài chính",
                "insights": "Phát hiện insights quan trọng và đưa ra khuyến nghị chiến lược",
                "json": "Trích xuất dữ liệu có cấu trúc JSON với các chỉ số quan trọng"
            }

            analysis_prompt = f"{prompts_map.get(output_format, prompts_map['detailed'])}\n\nNỘI DUNG:\n{combined_text}"

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Bạn là chuyên gia phân tích báo cáo tài chính của VTC NETVIET."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=3000
            )

            analysis_result = response.choices[0].message.content
            total_tokens += response.usage.total_tokens

            results["analysis"] = {
                "output_format": output_format,
                "result": analysis_result
            }

        # 5. Statistics
        results["statistics"] = {
            "total_tokens_used": total_tokens,
            "pdf_processed": pdf_file is not None,
            "images_processed": len(image_files) if image_files else 0,
            "charts_created": results["charts"].get("count", 0) if create_charts else 0,
            "output_format": output_format
        }

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chart/render")
async def render_chart_from_config(
    chart_config: Dict[str, Any] = Body(...),
    style: str = Body("seaborn")
):
    """
    Vẽ biểu đồ từ config đã tạo bởi Smart Chart Generator

    **Input:** Chart config từ /api/pipeline/full

    **Output:** File PNG biểu đồ
    """
    try:
        buffer = create_chart(
            data=chart_config["data"],
            chart_type=chart_config["chart_type"],
            title=chart_config["title"],
            xlabel=chart_config.get("xlabel"),
            ylabel=chart_config.get("ylabel"),
            style=style
        )

        return StreamingResponse(
            buffer,
            media_type="image/png",
            headers={
                "Content-Disposition": f"attachment; filename={chart_config['title'].replace(' ', '_')}.png",
                "X-Chart-Title": chart_config['title']
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chart/render-all")
async def render_all_charts(
    chart_configs: List[Dict[str, Any]] = Body(...),
    output_format: str = Body("zip", description="zip hoặc individual")
):
    """
    Vẽ tất cả biểu đồ từ danh sách configs

    **Output:**
    - zip: File ZIP chứa tất cả biểu đồ
    - individual: Trả về danh sách base64 images
    """
    try:
        if output_format == "zip":
            # Tạo ZIP file
            zip_buffer = io.BytesIO()

            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for i, config in enumerate(chart_configs, 1):
                    # Tạo biểu đồ
                    chart_buffer = create_chart(
                        data=config["data"],
                        chart_type=config["chart_type"],
                        title=config["title"],
                        xlabel=config.get("xlabel"),
                        ylabel=config.get("ylabel"),
                        style="seaborn"
                    )

                    # Thêm vào ZIP
                    filename = f"{i}_{config['title'].replace(' ', '_')}.png"
                    zip_file.writestr(filename, chart_buffer.getvalue())

            zip_buffer.seek(0)

            return StreamingResponse(
                zip_buffer,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename=charts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                }
            )

        else:  # individual
            results = []

            for config in chart_configs:
                chart_buffer = create_chart(
                    data=config["data"],
                    chart_type=config["chart_type"],
                    title=config["title"],
                    xlabel=config.get("xlabel"),
                    ylabel=config.get("ylabel"),
                    style="seaborn"
                )

                # Convert to base64
                base64_image = base64.b64encode(chart_buffer.getvalue()).decode('utf-8')

                results.append({
                    "title": config["title"],
                    "chart_type": config["chart_type"],
                    "image_base64": base64_image
                })

            return {
                "success": True,
                "count": len(results),
                "charts": results
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DEMO ENDPOINTS ====================

@app.get("/api/demo/chart-examples")
async def chart_examples():
    """
    Lấy danh sách ví dụ về các loại biểu đồ
    """
    examples = {
        "line_chart": {
            "description": "Biểu đồ đường theo dõi xu hướng",
            "data": {
                "x": ["Q1", "Q2", "Q3", "Q4"],
                "y": [100, 120, 115, 140],
                "label": "Doanh thu (tỷ VNĐ)"
            },
            "chart_type": "line",
            "title": "Doanh thu theo quý 2024"
        },
        "bar_chart": {
            "description": "Biểu đồ cột so sánh",
            "data": {
                "x": ["Sản phẩm A", "Sản phẩm B", "Sản phẩm C"],
                "y": [45, 60, 38]
            },
            "chart_type": "bar",
            "title": "So sánh doanh số sản phẩm"
        },
        "pie_chart": {
            "description": "Biểu đồ tròn thị phần",
            "data": {
                "labels": ["VTC", "Đối thủ A", "Đối thủ B", "Khác"],
                "values": [35, 25, 20, 20]
            },
            "chart_type": "pie",
            "title": "Thị phần thị trường 2024"
        },
        "scatter_chart": {
            "description": "Biểu đồ phân tán",
            "data": {
                "x": [1, 2, 3, 4, 5, 6, 7, 8],
                "y": [2, 4, 3, 5, 7, 6, 8, 9],
                "sizes": [50, 100, 150, 200, 100, 50, 200, 150]
            },
            "chart_type": "scatter",
            "title": "Mối quan hệ chi phí - lợi nhuận"
        },
        "heatmap": {
            "description": "Bản đồ nhiệt",
            "data": {
                "matrix": [
                    [1.2, 2.3, 3.1, 2.8],
                    [2.1, 3.5, 4.2, 3.9],
                    [1.8, 2.9, 3.8, 4.5]
                ],
                "xlabels": ["Q1", "Q2", "Q3", "Q4"],
                "ylabels": ["Miền Bắc", "Miền Trung", "Miền Nam"]
            },
            "chart_type": "heatmap",
            "title": "Hiệu suất theo khu vực & quý"
        }
    }

    return {
        "success": True,
        "examples": examples,
        "usage": "Sử dụng data từ examples này với endpoint POST /api/chart/create"
    }


@app.get("/api/demo/analysis-examples")
async def analysis_examples():
    """
    Ví dụ về các loại phân tích
    """
    return {
        "text_analysis": {
            "endpoint": "POST /api/analyze/text",
            "types": {
                "summary": "Tóm tắt điều hành ngắn gọn",
                "detailed": "Phân tích chi tiết toàn diện",
                "insights": "Phát hiện insight và khuyến nghị",
                "qa": "Tạo câu hỏi và trả lời",
                "json": "Trích xuất dữ liệu có cấu trúc"
            }
        },
        "image_analysis": {
            "endpoint": "POST /api/analyze/image",
            "types": {
                "chart": "Phân tích biểu đồ",
                "table": "Trích xuất bảng dữ liệu",
                "data": "Lấy tất cả số liệu",
                "general": "Phân tích chung"
            }
        },
        "smart_chart": {
            "endpoint": "POST /api/chart/smart",
            "examples": [
                "Vẽ biểu đồ cột doanh thu Q1-Q4: 100, 120, 115, 140 tỷ",
                "Tạo biểu đồ tròn thị phần: VTC 35%, Đối thủ A 25%, Khác 40%",
                "Vẽ đường xu hướng tăng trưởng từ 2020-2024: 50, 65, 80, 95, 110 tỷ"
            ]
        },
        "smart_chart_generator": {
            "endpoint": "POST /api/pipeline/full",
            "description": "Tự động trích xuất dữ liệu và tạo nhiều biểu đồ",
            "parameters": {
                "pdf_file": "File PDF báo cáo",
                "text_content": "Yêu cầu tạo biểu đồ",
                "create_charts": "true/false",
                "output_format": "summary/detailed/insights"
            }
        }
    }


# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("🚀 STARTING API SERVER - AI ĐỌC BÁO CÁO VTC NETVIET v2.0")
    print("=" * 80)
    print("\n📡 Server Information:")
    print(f"   - Host: http://localhost:8502")
    print(f"   - API Docs: http://localhost:8502/docs")
    print(f"   - ReDoc: http://localhost:8502/redoc")
    print(f"   - Homepage: http://localhost:8502/")
    print("\n🆕 New Features:")
    print("   - ⚡ Smart Chart Generator")
    print("   - 📊 Auto extract data from financial reports")
    print("   - 🎨 Generate multiple charts automatically")
    print("   - 📦 Export charts as PNG or ZIP")
    print("\n🔧 Available Endpoints:")
    print("   - POST /api/pipeline/full - Pipeline hoàn chỉnh + Smart Charts")
    print("   - POST /api/chart/render - Vẽ biểu đồ từ config")
    print("   - POST /api/chart/render-all - Vẽ tất cả biểu đồ (ZIP)")
    print("   - POST /api/analyze/text - Phân tích văn bản")
    print("   - POST /api/analyze/image - Phân tích ảnh/biểu đồ")
    print("   - POST /api/analyze/pdf - Phân tích PDF")
    print("   - POST /api/chart/create - Vẽ biểu đồ từ dữ liệu")
    print("   - POST /api/chart/smart - Tạo biểu đồ từ mô tả")
    print("   - POST /api/reports/compare - So sánh báo cáo")
    print("   - GET /api/demo/chart-examples - Ví dụ biểu đồ")
    print("=" * 80)
    print("\n⚙️  Starting server...\n")

    uvicorn.run(
        "api_service:app",
        host="0.0.0.0",
        port=8502,
        reload=True,
        log_level="info"
    )