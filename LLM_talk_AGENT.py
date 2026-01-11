from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import base64
import os
import traceback
from urllib import request, parse
from datetime import datetime
from run_top import DualSerialHandler
from cozepy import COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Message, ChatEventType

# ================ 配置 ================
MIC_DEVICE_ID = 1  # 麦克风ID
SPEAKER_DEVICE_ID = 4  # 扬声器ID
BAIDU_API_KEY = XXXX  # 替换为你的百度API Key
BAIDU_SECRET_KEY = XXX  # 替换为你的百度Secret Key
# Coze配置 替换为你的Coze API Key
COZE_API_TOKEN = XXX
COZE_API_BASE = COZE_CN_BASE_URL
COZE_BOT_ID = XXX
COZE_USER_ID = XXX
COZE_CONVERSATION_ID = XXX
PORT = 8000  # 服务端口
HTML_FILE = "contact2.html"  # 前端文件名
MAX_RETRIES = 2  # 识别重试次数
TIMEOUT = 15  # 接口超时时间(秒)


# ================ 初始化 ================
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(CURRENT_DIR, HTML_FILE)

# 初始化Coze客户端
coze = Coze(auth=TokenAuth(token=COZE_API_TOKEN), base_url=COZE_API_BASE)

# 打印启动信息
print(f"===== 服务配置 =====")
print(f"前端文件: {HTML_PATH}")
print(f"麦克风ID: {MIC_DEVICE_ID} | 扬声器ID: {SPEAKER_DEVICE_ID}")
print(f"Coze机器人小奕ID: {COZE_BOT_ID}")
print(f"====================\n")


# 日志函数（带时间戳）
def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


# 错误处理装饰器
def handle_errors(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"{func.__name__} 错误: {str(e)}"
            log(error_msg)
            log(traceback.format_exc())  # 打印详细堆栈信息
            return f"处理错误: {str(e)}"

    return wrapper


# 获取当前日期和星期
def get_current_date_info():
    now = datetime.now()
    # 星期映射表
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday = weekdays[now.weekday()]
    # 格式化日期为 "YYYY年MM月DD日"
    date_str = now.strftime("%Y年%m月%d日")
    return date_str, weekday


# ================ 百度语音识别 ================
@handle_errors
def get_baidu_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": BAIDU_API_KEY,
        "client_secret": BAIDU_SECRET_KEY
    }

    try:
        req = request.Request(f"{url}?{parse.urlencode(params)}")
        with request.urlopen(req, timeout=TIMEOUT) as res:
            # 检查响应状态码
            if res.status != 200:
                raise Exception(f"HTTP错误状态码: {res.status}")

            response_data = res.read().decode()
            # 验证JSON格式
            try:
                data = json.loads(response_data)
            except json.JSONDecodeError:
                raise Exception(f"无效的JSON响应: {response_data[:100]}...")

            token = data.get("access_token")
            if not token:
                raise Exception(f"获取令牌失败: {data}")
            return token
    except Exception as e:
        raise Exception(f"令牌获取失败: {str(e)}")


@handle_errors
def baidu_stt(audio_bytes):
    """百度语音识别核心逻辑，支持空结果重试"""
    if not audio_bytes or len(audio_bytes) < 1024:  # 检查音频数据有效性
        raise Exception("无效的音频数据，长度过短")

    log(f"[DSP] 处理音频 (长度: {len(audio_bytes)}字节)")
    token = get_baidu_token()

    if not token:
        raise Exception("无法获取百度API令牌")

    url = "https://vop.baidubce.com/server_api"
    payload = {
        "format": "wav",
        "rate": 16000,
        "channel": 1,
        "token": token,
        "cuid": "python-client",
        "speech": base64.b64encode(audio_bytes).decode(),
        "len": len(audio_bytes)
    }

    try:
        req = request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}
        )

        with request.urlopen(req, timeout=TIMEOUT) as res:
            if res.status != 200:
                raise Exception(f"HTTP错误状态码: {res.status}")

            response_data = res.read().decode()
            try:
                result = json.loads(response_data)
            except json.JSONDecodeError:
                raise Exception(f"无效的JSON响应: {response_data[:100]}...")

            if result.get("err_no") != 0:
                err_msg = f"识别失败 ({result.get('err_no', '未知错误')}): {result.get('err_msg', '无错误信息')}"
                raise Exception(err_msg)

            text = result.get("result", [""])[0].strip()
            if not text:
                log(f"[DSP] 识别结果为空，触发重试")
                return "RETRY"

            log(f"[DSP] 识别结果: {text}")
            return text
    except Exception as e:
        raise Exception(f"语音识别失败: {str(e)}")


# ================ Coze智能体调用 ================
@handle_errors
def query_coze(text):
    """调用Coze智能体生成回复"""
    if not text or len(text.strip()) == 0:
        raise Exception("输入文本为空，无法调用智能体")

    # 获取当前日期和星期
    current_date, current_weekday = get_current_date_info()

    # 检查是否是与时间相关的问题
    time_related_keywords = ["今天", "星期", "日期", "几号", "几点", "时间"]
    is_time_related = any(keyword in text for keyword in time_related_keywords)

    # 如果是时间相关问题，在查询中加入当前时间信息
    enhanced_text = text
    if is_time_related:
        enhanced_text = f"{text}（当前时间：{current_date}，{current_weekday}）"

    log(f"[Coze] 发送请求: {text[:20]}...")

    try:
        bot_response = ""

        # 发送流式聊天请求到Coze
        for event in coze.chat.stream(
                bot_id=COZE_BOT_ID,
                user_id=COZE_USER_ID,
                conversation_id=COZE_CONVERSATION_ID,
                additional_messages=[
                    Message.build_user_question_text(enhanced_text),
                ],
        ):
            if event.event == ChatEventType.CONVERSATION_MESSAGE_DELTA:
                # 收集机器人的回复
                content = event.message.content or ""
                bot_response += content

            # if event.event == ChatEventType.CONVERSATION_CHAT_COMPLETED:
            #     # 获取token使用情况（可选）
            #     token_usage = event.chat.usage.token_count if event.chat.usage else None
            #     if token_usage is not None:
            #         log(f"[Coze] 本次对话消耗token: {token_usage}")

        if not bot_response:
            raise Exception("Coze智能体返回空回复")

        log(f"[Coze] 回复生成: {bot_response[:20]}...")
        return bot_response

    except Exception as e:
        raise Exception(f"Coze智能体交互失败: {str(e)}")


# ================ HTTP服务 ================
class ServerHandler(BaseHTTPRequestHandler):
    # 禁止默认日志（用自定义log替代）
    def log_message(self, format, *args):
        pass

    # 重写send_error方法以支持中文
    def send_error(self, code, message=None, **kwargs):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            # 准备错误页面内容
            error_message = message or self.responses[code][0]
            content = f"""
            <html>
                <head><title>{code} {error_message}</title></head>
                <body>
                    <h1>{code} {error_message}</h1>
                    <p>请检查您的请求或联系管理员</p >
                </body>
            </html>
            """
            self.wfile.write(content.encode('utf-8'))
        except Exception as e:
            log(f"发送错误响应失败: {str(e)}")

    # 处理预检请求
    def do_OPTIONS(self):
        try:
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
        except Exception as e:
            log(f"OPTIONS请求处理错误: {str(e)}")

    # 处理GET请求（返回前端页面）
    def do_GET(self):
        try:
            # 仅支持根路径和前端文件请求
            if self.path == "/" or self.path == f"/{HTML_FILE}":
                if not os.path.exists(HTML_PATH):
                    self.send_error(404, "页面未找到")
                    return

                # 尝试读取文件
                try:
                    with open(HTML_PATH, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    # 尝试不同编码
                    with open(HTML_PATH, "r", encoding="gbk") as f:
                        content = f.read()

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode('utf-8'))  # 明确指定utf-8编码
            else:
                self.send_error(404, "页面未找到")
        except Exception as e:
            log(f"GET请求处理错误: {str(e)}")
            self.send_error(500, f"服务器错误: {str(e)}")

    # 处理语音交互请求
    def do_POST(self):
        try:
            if self.path != "/stt":
                self.send_error(404, "接口未找到")
                return

            # 验证Content-Length
            if "Content-Length" not in self.headers:
                raise ValueError("缺少Content-Length头部")

            try:
                content_len = int(self.headers["Content-Length"])
                if content_len <= 0 or content_len > 10 * 1024 * 1024:  # 限制最大10MB
                    raise ValueError(f"无效的内容长度: {content_len}")
            except ValueError:
                raise ValueError("无效的Content-Length值")

            # 读取并解析请求体
            post_data = self.rfile.read(content_len)
            if not post_data:
                raise ValueError("请求体为空")

            try:
                data = json.loads(post_data)
            except json.JSONDecodeError:
                raise ValueError(f"无效的JSON格式: {post_data[:100]}...")

            log(f"[请求] 收到语音数据 (长度: {len(post_data)}字节)")

            # 验证音频数据
            audio_str = data.get("audio", "")
            if not audio_str:
                raise ValueError("无音频数据")

            # 提取base64数据
            try:
                audio_base64 = audio_str.split(",")[1] if "," in audio_str else audio_str
                audio_bytes = base64.b64decode(audio_base64)
            except (base64.binascii.Error, IndexError):
                raise ValueError("音频数据解码失败，无效的base64格式")

            # 语音识别（带重试）
            recognized_text = ""
            retries = 0
            while retries < MAX_RETRIES:
                result = baidu_stt(audio_bytes)
                if result == "RETRY":
                    retries += 1
                    log(f"[请求] 识别重试 ({retries}/{MAX_RETRIES})")
                else:
                    recognized_text = result
                    break

            if "识别失败" in recognized_text or retries >= MAX_RETRIES or not recognized_text:
                raise Exception(f"识别失败: {recognized_text}")

            # 调用Coze智能体
            coze_reply = query_coze(recognized_text)
            if "处理错误" in coze_reply or not coze_reply:
                raise Exception(f"Coze智能体回复异常: {coze_reply}")

            # ================ 关键部分：保留DualSerialHandler调用 ================
            # 将识别文本和回复传递给handle_new_command
            handler = DualSerialHandler()  # 创建实例
            handler.handle_new_command(cmd='111', keyword=coze_reply)  # 调用方法
            # =================================================================

            # 构造响应
            response = {
                "status": "success",
                "user_text": recognized_text,
                "reply": coze_reply,
                "device_info": {
                    "mic_id": MIC_DEVICE_ID,
                    "speaker_id": SPEAKER_DEVICE_ID
                }
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

            log(f"[请求] 响应发送完成")

        except Exception as e:
            # 错误处理
            error_msg = f"处理失败: {str(e)}"
            log(f"[请求] {error_msg}")

            try:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": error_msg,
                    "details": str(e)  # 提供详细错误信息用于调试
                }).encode())
            except Exception as send_err:
                log(f"错误响应发送失败: {str(send_err)}")


# ================ 启动服务 ================
if __name__ == "__main__":
    try:
        server = HTTPServer(("0.0.0.0", PORT), ServerHandler)
        log(f"服务启动成功")
        server.serve_forever()
    except KeyboardInterrupt:
        log("服务被用户终止")
        server.shutdown()
    except Exception as e:
        log(f"服务启动失败: {str(e)}")
        log(traceback.format_exc())
