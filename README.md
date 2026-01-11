
# Voice-LLM-SCARA-Robot

**智能语音交互与视觉引导 SCARA 机械臂系统**
**Intelligent Voice Interaction & Vision Guided SCARA Robotic Arm System**


## <a name="项目介绍"></a>项目介绍

这是一个基于 Python 多线程架构的智能机械臂控制系统，实现了从语音指令到物理执行的全流程自动化。项目融合了 **Coze 平台定制智能体** 的语义理解能力与 **自行训练的 ONNX 模型** 的视觉感知能力。它不依赖封装好的商业控制软件，而是通过手写底层驱动与运动学算法，将大语言模型与边缘侧视觉推理深度结合，能够在本地高效完成桌面物品的分拣与清理任务。

**功能概览**
在**交互层**，用户通过 Web 前端 `contact2.html` 进行语音或文本输入。后台服务 `LLM_talk_AGENT.py` 充当智能中枢，它通过 API 对接了**我们在 Coze 平台上适配开发的智能体**，能够将模糊的自然语言（如“把左边的铅笔拿走”）解析为标准的 JSON 控制帧，实现了精准的意图识别。
在**感知层**，视觉核心 `detect_new1.py` 加载了**基于 YOLOv5 架构自行训练的 `best_1.onnx` 模型**。该模型基于自建数据集训练而成（涵盖 **Eraser, Scale, Pencil, Sharpener, Paper** 五类常见文具），确保系统能以 640x640 分辨率实时定位目标。
在**执行层**，主控程序 `run_top.py` 负责全局多线程调度。它调用 `scara_1.py` 中的逆运动学算法将坐标转化为电机脉冲，并通过串口发送给下位机 `v0_1.ino` 实现精准抓取；针对特定任务，`run_1.py` 则封装了自动清理等复杂的连续动作逻辑。

## 📂 系统模块与文件说明

### 1. 核心控制模块 (Core Control)

* **`run_top.py`** (主控制程序)
* 负责机械臂双串口通信管理与指令调度。
* 内置防冲突保护与超时自动清理机制。
* 统筹复位、自动清理、单物品抓取等多线程任务。


* **`LLM_talk_AGENT.py`** (语音交互服务)
* 启动 HTTP 服务器提供 Web 交互界面。
* 集成语音识别 (STT) 与 Coze-DeepSeek 智能体对话逻辑。
* 负责音频格式转换及将自然语言转译为机械臂控制指令。



### 2. 机械臂控制模块 (Arm Control)

* **`scara_1.py`** (底层驱动)
* 实现 SCARA 机械臂运动学正逆解计算。
* 负责关节空间与笛卡尔空间的映射及串口指令封装。


* **`run_1.py`** (自动化逻辑)
* 封装分步抓取与放置的完整状态机流程。
* 实现连续物体检测机制与异常复位处理。



### 3. 视觉识别模块 (Computer Vision)

* **`detect_new1.py`** (物体检测)
* 基于 YOLOv5 ONNX 模型进行实时推理。
* 处理摄像头图像流，输出物品类别、坐标位置及置信度。



### 4. 前端与资源 (Frontend & Resources)

* **`contact2.html`** (Web 界面)
* 提供实时状态显示与响应式操作面板。
* 通过浏览器实现语音录音与播放功能。


* **`best_1.onnx`** (检测模型)
* 输入：640×640 RGB 图像。
* 输出：5 类文具目标的类别与位置信息。



## 🤖 硬件固件 (Firmware)

### **`v0_1.ino` (Arduino Control)**

SCARA 机械臂的底层控制程序，负责接收上位机指令并驱动硬件。

* **硬件控制**：
* 4 个步进电机：控制  旋转关节及 Z 轴升降。
* 1 个伺服电机：控制末端夹爪开合。
* 4 个限位开关：用于各轴自动回零校准。


* **通信协议**：
* 波特率：`115200`。
* 格式：接收 10 个逗号分隔的整数指令。
* 反馈：指令执行完毕后返回 `"DONE"` 信号，形成闭环控制。


* **运动特性**：
* 支持多轴协同插补运动，确保同步性。
* 实时响应中断指令。



## 🚀 运行说明

1. **环境配置**：
* 安装 Python 依赖：`pip install -r requirements.txt`。
* 硬件连接：将 Arduino 连接至 USB 串口（默认 COM7），连接 USB 摄像头。


2. **启动系统**：
* 运行主程序：`python run_top.py`。
* 系统将自动初始化视觉线程、语音服务及机械臂连接。


3. **开始交互**：
* 打开浏览器访问控制台输出的本地地址（通常为 `http://localhost:8000/contact2.html`）。



更加详细的逻辑请见代码注释，如有相关问题和漏洞恳请批评指正。

---

## <a name="overview"></a>Overview

This project implements a multi-threaded intelligent robotic arm control system based on Python, achieving full automation from voice command to physical execution. It integrates the semantic understanding of a **custom Coze Agent** with the visual perception of a **self-trained ONNX model**. Abandoning commercial black-box controllers, this system combines Large Language Models (LLM) with edge-side visual inference through custom low-level drivers and kinematics algorithms, efficiently performing desktop organization and sorting tasks locally.

**Features**
**Interaction Layer**: Users interact via the `contact2.html` Web interface using voice or text. The backend service `LLM_talk_AGENT.py` acts as the intelligent hub, interfacing with our **adapted Coze Agent** via API to parse ambiguous natural language (e.g., "Take away the pencil on the left") into standardized JSON control frames.
**Perception Layer**: The vision core `detect_new1.py` loads a **YOLOv5-based custom trained `best_1.onnx` model**. Trained on a custom dataset covering **Eraser, Scale, Pencil, Sharpener, and Paper**, it ensures real-time localization at 640x640 resolution.
**Execution Layer**: The main controller `run_top.py` manages global thread scheduling. It invokes inverse kinematics in `scara_1.py` to convert coordinates into motor pulses, communicating with the Arduino firmware `v0_1.ino` via UART. `run_1.py` encapsulates complex sequential logic for tasks like auto-cleaning.

*(Please refer to the Chinese section above for detailed module descriptions and hardware specifications.)*
