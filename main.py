# main.py - 4D场景生成后端API（完整版：AI功能 + 模拟接口）

import uvicorn
from datetime import datetime
from typing import Optional, Dict, Any, List
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# FastAPI核心依赖
from fastapi import FastAPI, HTTPException, Depends, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# ==================== 第三方API依赖 ====================
import requests
import base64
import time
import json

# ==================== 数据库相关代码（已注释，保留接口） ====================
# 如需启用数据库，请取消注释并安装依赖：pip install sqlalchemy pymysql
#
# from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker
#
# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:123456@localhost/xingyu_rehab"
# engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()
#
# class AssessmentReport(Base):
#     __tablename__ = "assessment_reports"
#     id = Column(Integer, primary_key=True, index=True, autoincrement=True)
#     child_id = Column(Integer, nullable=False)
#     abc_score = Column(Integer, nullable=False)
#     cars_score = Column(Integer, nullable=False)
#     qualitative_eval = Column(Text, nullable=False)
#     pdf_path = Column(String(255), nullable=True)
#     created_at = Column(DateTime, default=datetime.now)
#
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
# ==================== 数据库代码结束 ====================


# ===================== 基础配置 =====================
app = FastAPI(
    title="4D康复场景生成API",
    description="孤独症儿童4D动态康复场景生成与评估报告管理后端",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== API密钥配置（从环境变量读取） =====================
# ===================== API密钥配置（从环境变量读取） =====================
# DeepSeek API（已禁用，可通过修改 ENABLE_DEEPSEEK 启用）
ENABLE_DEEPSEEK = False
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")  # 去掉默认值
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"

# 智谱API（主要使用）
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")  # 去掉默认值
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

# 百度千帆API配置
BAIDU_API_KEY = os.environ.get("BAIDU_API_KEY", "")  # 去掉默认值
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")  # 去掉默认值
BAIDU_TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"

baidu_access_token = None
baidu_token_expire_time = None


# ===================== 数据模型 =====================
class Generate4DRequest(BaseModel):
    prompt: str = Field(..., description="场景生成的文本提示词")
    image: Optional[str] = Field(None, description="可选的参考图片Base64编码")
    userId: Optional[str] = Field(None, description="用户ID")


class Generate4DResponse(BaseModel):
    success: bool = Field(..., description="请求是否成功")
    scene_type: str = Field(..., description="解析后的场景类型")
    message: str = Field(..., description="响应提示信息")
    scene_data: Optional[Dict[str, Any]] = Field(None, description="场景详细数据")
    task: str = Field(..., description="场景对应的康复任务")
    ai_enhanced: Optional[bool] = Field(False, description="是否使用AI增强")
    model_used: Optional[str] = Field(None, description="使用的模型")


class TextEnhanceRequest(BaseModel):
    text: str


class VoiceToTextRequest(BaseModel):
    audio_base64: str
    audio_format: str = "wav"


class ImageUnderstandRequest(BaseModel):
    image_base64: str
    prompt: str = "请描述这张图片的内容"


class AssessmentItem(BaseModel):
    child_id: int = Field(..., gt=0, description="儿童ID")
    abc_score: int = Field(..., ge=0, le=174, description="ABC量表得分")
    cars_score: int = Field(..., ge=0, le=60, description="CARS量表得分")
    qualitative_eval: str = Field(..., min_length=1, description="定性评估描述")
    pdf_path: Optional[str] = Field("", description="评估报告PDF存储路径")


class AssessmentResponse(BaseModel):
    code: int = Field(200, description="状态码")
    msg: str = Field(..., description="提示信息")
    report_id: Optional[int] = Field(None, description="评估报告ID")


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UpdateProgressRequest(BaseModel):
    child_id: int = Field(..., description="儿童ID")
    scene_type: str = Field(..., description="场景类型")
    completion_percent: int = Field(..., ge=0, le=100, description="完成百分比")


class SaveTrainingRecordRequest(BaseModel):
    child_id: int
    scene_type: str
    training_date: str
    participation_score: int
    mood_state: str
    completion_rate: int
    remark: Optional[str] = ""


class SaveScaleResultRequest(BaseModel):
    child_id: int
    scale_type: str
    total_score: int
    level: str
    assessment_date: str


# ===================== 核心常量 =====================
SCENE_MAPPING = {
    "公交": "bus", "巴士": "bus", "车": "bus", "公交车": "bus",
    "公园": "park", "秋千": "park", "草地": "park",
    "超市": "supermarket", "商店": "supermarket", "购物": "supermarket",
    "教室": "classroom", "学校": "classroom", "课堂": "classroom",
    "花园": "garden", "花朵": "garden", "花": "garden",
    "打雷": "thunder", "雷": "thunder", "闪电": "thunder"
}

TASKS = {
    "bus": "🚌 排队上车，学会刷卡并找座位",
    "park": "🌳 与小朋友轮流玩秋千，学习社交规则",
    "supermarket": "🛒 按清单拿取商品，学习购物礼仪",
    "classroom": "📚 听从老师指令，举手回答问题",
    "garden": "🌸 识别情绪卡片，观察花朵变化",
    "thunder": "⚡ 观察天气变化，学习应对雷雨天气"
}


# ===================== 工具函数 =====================
def parse_prompt(prompt: str) -> str:
    """解析提示词，匹配对应的场景类型"""
    if not prompt:
        return "garden"
    prompt_lower = prompt.strip().lower()
    for key, value in SCENE_MAPPING.items():
        if key in prompt_lower:
            return value
    return "garden"


# ===================== 百度千帆语音识别（修正版） =====================
def get_baidu_token():
    """获取百度千帆access_token（修正版）"""
    global baidu_access_token, baidu_token_expire_time

    # 检查缓存的token是否有效
    if baidu_access_token and baidu_token_expire_time and datetime.now().timestamp() < baidu_token_expire_time:
        return baidu_access_token

    try:
        url = f"{BAIDU_TOKEN_URL}?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"

        print(f"正在获取百度access_token...")
        response = requests.post(url, timeout=30)
        result = response.json()

        if "access_token" in result:
            baidu_access_token = result["access_token"]
            baidu_token_expire_time = datetime.now().timestamp() + result.get("expires_in", 2592000) - 3600
            print(f"百度token获取成功，过期时间: {datetime.fromtimestamp(baidu_token_expire_time)}")
            return baidu_access_token
        else:
            print(f"百度token获取失败: {result}")
            return None
    except Exception as e:
        print(f"百度token请求异常: {str(e)}")
        return None


def speech_to_text_baidu(audio_bytes):
    """百度千帆语音转文字 - 使用正确的API端点"""
    access_token = get_baidu_token()
    if not access_token:
        print("无法获取百度access_token")
        return None

    url = f"https://aip.baidubce.com/rpc/2.0/aasr/v1?access_token={access_token}"
    speech_base64 = base64.b64encode(audio_bytes).decode('utf-8')

    payload = {
        "format": "wav",
        "rate": 16000,
        "channel": 1,
        "cuid": "4d_scene_api",
        "token": access_token,
        "speech": speech_base64,
        "len": len(audio_bytes)
    }

    try:
        print(f"正在调用百度语音识别API，音频大小: {len(audio_bytes)} bytes")
        response = requests.post(url, json=payload, timeout=30)
        result = response.json()

        print(f"百度语音识别响应: {result}")

        if result.get("err_no") == 0:
            text = result.get("result", [""])[0]
            if text:
                print(f"语音识别成功: {text}")
                return text
            else:
                print("语音识别结果为空")
                return None
        else:
            error_messages = {
                3301: "音频质量错误，请确保是16kHz单声道WAV",
                3302: "语音过长",
                3303: "语音识别失败",
                3304: "鉴权失败",
                3305: "参数错误"
            }
            err_no = result.get("err_no")
            print(f"百度语音识别错误 {err_no}: {error_messages.get(err_no, result.get('err_msg', '未知错误'))}")
            return None
    except requests.exceptions.Timeout:
        print("百度语音识别请求超时")
        return None
    except Exception as e:
        print(f"百度语音识别异常: {str(e)}")
        return None


# ===================== 智谱API调用 =====================
def call_zhipu(messages, model="glm-4-flash", temperature=0.7, max_retries=3):
    """调用智谱API - 主要使用的AI模型"""
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": 2000
    }

    for attempt in range(max_retries):
        try:
            print(f"智谱API调用尝试 {attempt + 1}/{max_retries}...")
            print(f"请求模型: {model}")
            response = requests.post(ZHIPU_API_URL, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print("智谱API调用成功")
                print(f"响应内容预览: {content[:100]}...")
                return content
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 3
                print(f"智谱速率限制(429)，等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                print(f"智谱API错误: {response.status_code}")
                if response.text:
                    print(f"错误详情: {response.text[:200]}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
        except requests.exceptions.Timeout:
            print(f"智谱请求超时，重试 {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None
        except Exception as e:
            print(f"智谱API异常: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None


def call_zhipu_for_scene_classification(prompt: str, max_retries=3):
    """专门用于场景分类的智谱API调用 - 返回场景类型"""
    system_prompt = """你是孤独症康复训练专家。根据用户的描述，判断最适合的训练场景。
只返回以下场景类型中的一个词，不要有其他内容：
- bus: 公交车、巴士、交通工具相关
- supermarket: 超市、购物、商店相关  
- classroom: 教室、学校、课堂相关
- park: 公园、秋千、户外玩耍相关
- garden: 花园、花朵、自然观察相关

示例：
输入："我想坐公交车" -> 输出：bus
输入："去超市买东西" -> 输出：supermarket
输入："在学校上课" -> 输出：classroom
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    return call_zhipu(messages, max_retries=max_retries)


def call_zhipu_vision(image_base64, prompt, max_retries=2):
    """智谱图像理解 - 使用GLM-4V-Flash模型"""
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "glm-4v-flash",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                ]
            }
        ],
        "max_tokens": 1000
    }

    for attempt in range(max_retries):
        try:
            print(f"调用智谱图像理解API (尝试 {attempt + 1}/{max_retries})...")
            response = requests.post(ZHIPU_API_URL, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print("智谱图像理解成功")
                return content
            elif response.status_code == 429:
                wait_time = (attempt + 1) * 2
                print(f"图像理解速率限制，等待{wait_time}秒后重试...")
                time.sleep(wait_time)
                continue
            else:
                print(f"智谱图像理解错误: {response.status_code}")
                if response.text:
                    print(f"错误详情: {response.text[:200]}")
                return None
        except Exception as e:
            print(f"智谱图像理解异常: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None


def call_deepseek(messages, max_retries=2):
    """DeepSeek API调用 - 可选备用"""
    if not ENABLE_DEEPSEEK:
        print("DeepSeek已禁用，跳过")
        return None

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }

    for attempt in range(max_retries):
        try:
            print(f"DeepSeek API调用尝试 {attempt + 1}/{max_retries}...")
            response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=60)

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                print("DeepSeek API调用成功")
                return content
            else:
                print(f"DeepSeek API错误: {response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return None
        except Exception as e:
            print(f"DeepSeek API异常: {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None
    return None


# ===================== 统一AI调用（优先智谱） =====================
def call_ai(messages, task_name="AI调用"):
    """统一AI调用接口：优先使用智谱，可选DeepSeek作为备用"""
    print(f"\n========== {task_name} ==========")

    print("【第1步】调用智谱API...")
    result = call_zhipu(messages)
    if result:
        print(f"✅ 智谱成功")
        return result, "zhipu"

    if ENABLE_DEEPSEEK:
        print("【第2步】智谱失败，尝试DeepSeek...")
        result = call_deepseek(messages)
        if result:
            print(f"✅ DeepSeek成功")
            return result, "deepseek"

    print("❌ 所有AI都失败")
    return None, None


# ===================== 本地备用方案 =====================
def local_enhance_prompt(prompt: str) -> str:
    """本地语义增强 - 当所有AI都失败时使用"""
    enhancements = {
        "打雷": "雷电交加的雨天场景，天空中闪电划过，雷声隆隆，乌云密布，儿童学习观察天气变化，理解自然现象，克服对雷声的恐惧",
        "公交": "孤独症儿童公交车乘坐训练场景，一辆卡通风格的公交车停在公交站台，车门打开，儿童需要学习排队上车、刷卡、找座位坐下，场景温馨明亮，人物表情友善",
        "巴士": "孤独症儿童公交车乘坐训练场景，一辆卡通风格的公交车停在公交站台，车门打开，儿童需要学习排队上车、刷卡、找座位坐下，场景温馨明亮",
        "车": "儿童交通安全训练场景，学习认识车辆、等待、上车",
        "公园": "孤独症儿童公园社交训练场景，小朋友们在玩秋千、滑梯，学习轮流玩耍和社交互动",
        "秋千": "儿童感统训练场景，学习轮流荡秋千，等待和分享",
        "超市": "孤独症儿童超市购物训练场景，学习按照购物清单拿商品、排队结账",
        "教室": "孤独症儿童课堂训练场景，学习听老师指令、举手回答问题",
        "花园": "孤独症儿童情绪认知训练场景，观察花朵变化，识别情绪卡片"
    }
    for key, value in enhancements.items():
        if key in prompt:
            return value
    return f"孤独症儿童康复训练场景：{prompt}，场景温馨明亮，卡通风格，人物表情友善"


def local_reconstruct_text(text: str) -> str:
    """本地文本重构 - 当所有AI都失败时使用"""
    replacements = {
        "车车": "公交车",
        "怕怕": "害怕",
        "呜呜": "哭",
        "不要": "不想",
        "要要": "想要",
        "嘿嘿": "开心"
    }
    result = text
    for key, value in replacements.items():
        if key in result:
            result = result.replace(key, value)
    if result == text and len(text) > 0:
        return f"我想表达：{text}"
    return result


# ===================== API 路由 - 基础接口 =====================
@app.get("/", summary="根路径")
async def root():
    return {
        "message": "4D康复场景生成API服务运行中",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
        "database": "disabled (接口代码已保留，未实际连接)",
        "ai_models": {
            "primary": "智谱 GLM-4-Flash",
            "fallback": "本地备用方案",
            "speech": "百度千帆语音识别",
            "vision": "智谱 GLM-4V-Flash"
        }
    }


@app.get("/health", summary="健康检查")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "4D-scene-generator",
        "database": "not_connected"
    }


@app.get("/api/info", summary="API信息")
async def api_info():
    return {
        "name": "4D康复场景生成器",
        "version": "2.0.0",
        "supported_scenes": list(SCENE_MAPPING.keys()),
        "description": "基于文本描述生成4D动态康复场景",
        "database_enabled": False,
        "ai_models": {
            "text": "智谱 GLM-4-Flash (主要)",
            "speech": "百度千帆语音识别",
            "vision": "智谱 GLM-4V-Flash"
        }
    }


# ===================== API 路由 - AI功能 =====================
@app.post("/api/enhance-prompt")
async def enhance_prompt(request: TextEnhanceRequest):
    """治疗师指令语义增强 - 使用智谱API"""
    system_prompt = """你是一个孤独症康复训练专家，擅长优化康复训练指令。

任务：将用户的原始指令优化为更清晰、结构化、可执行的训练提示词。

优化要求：
1. 保持原意，不添加不相关内容
2. 使用简洁明确的语言
3. 添加必要的场景描述（如环境、人物、动作）
4. 输出格式：直接输出优化后的提示词，不要解释

示例：
输入："怕公交车"
输出："孤独症儿童公交车乘坐训练场景，一辆卡通风格的公交车停在公交站台，车门打开，儿童需要学习排队上车、刷卡、找座位坐下，场景温馨明亮，人物表情友善"
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.text}
    ]

    print(f"\n========== 语义增强 ==========")
    print(f"原始输入: {request.text}")

    result, model_used = call_ai(messages, "语义增强")

    use_local = False
    if result:
        enhanced = result
        print(f"✅ {model_used} 增强成功")
    else:
        print("❌ 所有AI失败，使用本地备用")
        enhanced = local_enhance_prompt(request.text)
        use_local = True
        model_used = "local-fallback"

    return {
        "success": True,
        "original": request.text,
        "enhanced": enhanced,
        "model": model_used,
        "use_fallback": use_local
    }


@app.post("/api/reconstruct-text")
async def reconstruct_text(request: TextEnhanceRequest):
    """患儿文本规范化重构 - 使用智谱API"""
    if len(request.text.strip()) < 2:
        return {
            "success": True,
            "original": request.text,
            "reconstructed": request.text,
            "model": "skip",
            "use_fallback": True
        }

    system_prompt = """你是一个儿童语言理解专家。

任务：将孤独症儿童说不规范的语句，改写成语法正确、逻辑清晰的规范语句。

要求：
1. 保持儿童的原始意图不变
2. 不要添加原句中不存在的内容
3. 用简单易懂的词汇
4. 输出格式：直接输出规范后的句子

示例：
输入："车车怕 呜呜 不要"
输出："我害怕公交车，不想坐公交车"
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": request.text}
    ]

    print(f"\n========== 文本重构 ==========")
    print(f"原始输入: {request.text}")

    result, model_used = call_ai(messages, "文本重构")

    use_local = False
    if result:
        reconstructed = result
        print(f"✅ {model_used} 重构成功")
    else:
        print("❌ 所有AI失败，使用本地备用")
        reconstructed = local_reconstruct_text(request.text)
        use_local = True
        model_used = "local-fallback"

    return {
        "success": True,
        "original": request.text,
        "reconstructed": reconstructed,
        "model": model_used,
        "use_fallback": use_local
    }


@app.post("/api/voice-to-text")
async def voice_to_text(request: VoiceToTextRequest):
    """语音转文字 - 百度千帆API"""
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
        audio_format = request.audio_format.lower()
        print(f"语音识别请求: 格式={audio_format}, 大小={len(audio_bytes)} bytes")

        text = speech_to_text_baidu(audio_bytes)

        if text:
            print(f"语音识别成功: {text}")
            return {
                "success": True,
                "text": text,
                "model": "百度千帆语音识别"
            }
        else:
            return {
                "success": False,
                "text": "",
                "message": "语音识别失败，请确保音频是16kHz单声道WAV格式，并重试"
            }
    except base64.binascii.Error as e:
        print(f"Base64解码错误: {str(e)}")
        raise HTTPException(status_code=400, detail="音频Base64编码无效")
    except Exception as e:
        print(f"语音转文字错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")


@app.post("/api/understand-image")
async def understand_image(request: ImageUnderstandRequest):
    """图像理解 - 智谱GLM-4V-Flash模型"""
    if not request.image_base64:
        raise HTTPException(status_code=400, detail="缺少image_base64参数")

    print(f"\n========== 图像理解 ==========")
    print(f"提示词: {request.prompt}")

    result = call_zhipu_vision(request.image_base64, request.prompt)

    if result:
        print("✅ 智谱图像理解成功")
        return {
            "success": True,
            "description": result,
            "model": "glm-4v-flash"
        }

    print("❌ 图像理解失败")
    raise HTTPException(status_code=500, detail="图像理解失败，请稍后重试")


# ===================== API 路由 - 4D场景生成（真正调用AI） =====================
@app.post("/api/generate-4d", summary="生成基础4D场景")
async def generate_4d_scene(request: dict):
    """4D场景生成接口 - 真正调用智谱AI进行场景分类"""
    try:
        prompt = request.get("prompt", "")
        user_id = request.get("userId", "guest")

        print(f"\n========== 4D场景生成 ==========")
        print(f"用户输入: {prompt}")
        print(f"用户ID: {user_id}")

        if not prompt:
            return {
                "success": False,
                "message": "请输入场景描述"
            }

        # 第一步：尝试用AI进行场景分类
        print("🤖 正在调用智谱AI进行场景分类...")
        ai_scene = call_zhipu_for_scene_classification(prompt)

        if ai_scene:
            scene_type = ai_scene.strip().lower()
            if scene_type in ["bus", "supermarket", "classroom", "park", "garden"]:
                print(f"✅ AI识别场景: {scene_type}")
                ai_used = True
                model_used = "zhipu-ai"
            else:
                print(f"⚠️ AI返回无效场景: {ai_scene}，使用关键词匹配")
                scene_type = parse_prompt(prompt)
                ai_used = False
                model_used = "keyword-fallback"
        else:
            print("❌ AI调用失败，使用关键词匹配")
            scene_type = parse_prompt(prompt)
            ai_used = False
            model_used = "local-fallback"

        # 第二步：用AI生成增强提示词
        enhanced_prompt = prompt
        if ai_used:
            enhance_messages = [
                {"role": "system", "content": "你是孤独症康复训练专家，请将用户描述优化为适合生成4D动态场景的详细提示词，直接输出优化结果，不要解释。"},
                {"role": "user", "content": prompt}
            ]
            enhance_result, _ = call_ai(enhance_messages, "4D场景增强")
            if enhance_result:
                enhanced_prompt = enhance_result
                print(f"✅ 提示词增强成功")

        print(f"📌 最终场景类型: {scene_type}")

        scene_data = {
            "scene_type": scene_type,
            "original_prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "dynamic_elements": ["moving_objects", "time_animation", "interactive_agents"],
            "duration": 30,
            "quality": "high",
            "generated_at": datetime.now().isoformat()
        }

        return {
            "success": True,
            "scene_type": scene_type,
            "message": f"成功生成4D场景: {scene_type}" + (" (使用AI智能识别)" if ai_used else " (关键词匹配)"),
            "scene_data": scene_data,
            "task": TASKS.get(scene_type, "完成社交互动任务"),
            "ai_enhanced": ai_used,
            "model_used": model_used
        }

    except Exception as e:
        print(f"生成错误: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"生成失败: {str(e)}"
        }


@app.post("/api/generate-advanced", summary="生成高级4D场景")
async def generate_advanced_4d(request: Generate4DRequest):
    """高级4D生成接口 - 使用智谱API"""
    enhance_messages = [
        {"role": "system", "content": "将以下描述优化为详细的4D场景生成提示词，直接输出优化结果："},
        {"role": "user", "content": request.prompt}
    ]

    result, model_used = call_ai(enhance_messages, "高级4D增强")

    if result:
        enhanced_prompt = result
    else:
        enhanced_prompt = local_enhance_prompt(request.prompt)
        model_used = "local-fallback"

    scene_type = parse_prompt(request.prompt)
    return {
        "success": True,
        "scene_type": scene_type,
        "enhanced_prompt": enhanced_prompt,
        "model_used": model_used,
        "scene_url": f"/scenes/{datetime.now().timestamp()}.glb",
        "animation_url": f"/animations/{datetime.now().timestamp()}.mp4",
        "parameters": {
            "spatial_consistency": 0.95,
            "temporal_coherence": 0.92,
            "dynamic_range": "high"
        }
    }


# ===================== API 路由 - 用户认证（模拟） =====================
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录（模拟接口，不连接数据库）"""
    if request.username == "therapist1":
        role = "therapist"
        user_id = 1
        child_name = None
        therapist_id = None
    else:
        role = "child"
        user_id = 2
        child_name = request.username
        therapist_id = 1

    return {
        "success": True,
        "token": f"mock_token_{int(datetime.now().timestamp())}",
        "user": {
            "user_id": user_id,
            "username": request.username,
            "role": role,
            "child_name": child_name,
            "therapist_id": therapist_id,
            "progress": {"bus": 30, "supermarket": 20, "classroom": 0, "park": 0, "garden": 0}
        }
    }


@app.post("/api/register")
async def register(username: str, password: str, role: str = "child"):
    """用户注册（模拟接口）"""
    return {
        "success": True,
        "message": "注册成功（演示模式）",
        "user_id": int(datetime.now().timestamp())
    }


@app.get("/api/child-list/{therapist_id}")
async def get_child_list(therapist_id: int):
    """获取治疗师名下的患儿列表（模拟数据）"""
    return {
        "success": True,
        "children": [
            {"user_id": 2, "username": "小明", "child_name": "小明"},
            {"user_id": 3, "username": "小红", "child_name": "小红"}
        ]
    }


# ===================== API 路由 - 训练进度 =====================
@app.post("/api/update-progress")
async def update_progress(request: UpdateProgressRequest):
    """更新患儿场景进度（模拟接口）"""
    return {
        "success": True,
        "message": "进度已更新（演示模式）",
        "child_id": request.child_id,
        "scene_type": request.scene_type,
        "completion_percent": request.completion_percent
    }


@app.post("/api/save-training-record")
async def save_training_record(request: SaveTrainingRecordRequest):
    """保存训练记录（模拟接口）"""
    return {
        "success": True,
        "message": "训练记录已保存（演示模式）",
        "record_id": int(datetime.now().timestamp())
    }


@app.get("/api/training-records/{child_id}")
async def get_training_records(child_id: int):
    """获取患儿的训练记录（模拟数据）"""
    return {
        "success": True,
        "records": [
            {
                "id": 1,
                "child_id": child_id,
                "scene_type": "bus",
                "training_date": datetime.now().strftime("%Y-%m-%d"),
                "participation_score": 85,
                "mood_state": "happy",
                "completion_rate": 80,
                "remark": "表现良好"
            }
        ]
    }


# ===================== API 路由 - 量表评估 =====================
@app.post("/api/save-scale-result")
async def save_scale_result(request: SaveScaleResultRequest):
    """保存量表评估结果（模拟接口）"""
    return {
        "success": True,
        "message": "量表结果已保存（演示模式）",
        "assessment_id": int(datetime.now().timestamp())
    }


@app.get("/api/scale-assessments/{child_id}")
async def get_scale_assessments(child_id: int):
    """获取患儿的量表评估记录（模拟数据）"""
    return {
        "success": True,
        "assessments": [
            {
                "id": 1,
                "child_id": child_id,
                "scale_type": "CARS",
                "total_score": 35,
                "level": "轻度孤独症",
                "assessment_date": datetime.now().strftime("%Y-%m-%d")
            }
        ]
    }


@app.post("/api/save-assessment", summary="保存评估报告")
async def save_assessment(assessment: AssessmentItem):
    """保存评估报告（模拟接口）"""
    return AssessmentResponse(
        code=200,
        msg="评估报告已保存（演示模式，未实际存储）",
        report_id=int(datetime.now().timestamp())
    )


@app.get("/api/get-assessments/{child_id}", summary="查询儿童评估报告")
async def get_assessments(child_id: int = Path(..., gt=0)):
    """查询评估报告（模拟数据）"""
    return {
        "code": 200,
        "data": [],
        "msg": f"演示模式：未找到ID为{child_id}的儿童评估报告"
    }


# ===================== 启动服务 =====================
if __name__ == "__main__":
    print("=" * 50)
    print("4D康复场景生成API服务启动")
    print("=" * 50)
    print(f"智谱API状态: {'已配置' if ZHIPU_API_KEY else '未配置'}")
    print(f"百度语音识别: {'已配置' if BAIDU_API_KEY else '未配置'}")
    print(f"DeepSeek: {'已启用' if ENABLE_DEEPSEEK else '已禁用'}")
    print("=" * 50)
    print(f"API文档: http://localhost:8000/docs")
    print(f"服务地址: http://localhost:8000")
    print("=" * 50)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )