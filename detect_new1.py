import cv2
import numpy as np


def detect_camera():
    # 配置参数
    weights_path = r"/best_1.onnx"  # 模型路径，修改为实际路径
    camera_device = 0  # 摄像头设备索引或路径
    input_w, input_h = 640, 640 # 模型输入尺寸
    conf_thres = 0.60# 置信度阈值
    nms_thres = 0.35  # NMS阈值
    class_names = ["pen", "eraser", "sharpener", "scale", "paper"]  # 类别名称

    # 加载模型
    try:
        net = cv2.dnn.readNetFromONNX(weights_path)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    # print(f"模型加载成功: {weights_path}")
    except Exception as e:
        raise RuntimeError(f"模型加载失败: {str(e)}")
    # 打开摄像头
    cap = cv2.VideoCapture(camera_device)
    if not cap.isOpened():
        # 尝试作为设备路径打开
        cap = cv2.VideoCapture(f"/dev/video{camera_device}")
        if not cap.isOpened():
            raise IOError(f"无法打开摄像头设备: {camera_device}")


    # 设置摄像头参数
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # 读取一帧
    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise IOError("无法获取摄像头图像")

  #  print(f"图像尺寸: {frame.shape[1]}x{frame.shape[0]}")
    orig_h, orig_w = frame.shape[:2]

    # 图像预处理
    blob = cv2.dnn.blobFromImage(
        frame, 1 / 255.0,  (input_w, input_h), swapRB=True, crop=False)
    net.setInput(blob)
    # 推理（获取输出层）
    outputs = net.forward(net.getUnconnectedOutLayersNames())


    # 关键修正：YOLOv5的ONNX输出是(1, 25200, 85)格式（85=4坐标+1置信度+80类别）
    # 需将输出重塑为(25200, 85)
    outputs = np.squeeze(outputs[0])  # 去除批次维度

    boxes, confs, class_ids = [], [], []
    for det in outputs:
        # 解析每个检测框：前4个是坐标(cx, cy, w, h)，第5个是目标置信度
        cx, cy, w, h, obj_conf = det[:5]
        # 类别分数从第6个元素开始（根据你的类别数量截取）
        cls_scores = det[5:5 + len(class_names)]  # 只取实际类别数量的分数

        # 防止索引越界（核心修正）
        if len(cls_scores) == 0:
            continue
        cls_id = np.argmax(cls_scores)
        if cls_id >= len(class_names):
            continue  # 跳过超出类别定义的结果

        # 计算最终置信度并过滤
        final_conf = obj_conf * cls_scores[cls_id]
        if final_conf > conf_thres:
            # 坐标转换为左上角(x1, y1)和宽高(w, h)
            x1 = int((cx - w / 2) * orig_w / input_w)
            y1 = int((cy - h / 2) * orig_h / input_h)
            w_box = int(w * orig_w / input_w)
            h_box = int(h * orig_h / input_h)

            boxes.append([x1, y1, w_box, h_box])
            confs.append(float(final_conf))
            class_ids.append(cls_id)

    # NMS去重
    indices = cv2.dnn.NMSBoxes(boxes, confs, conf_thres, nms_thres)
    result = [
        [class_names[class_ids[i]],
         boxes[i][0] + boxes[i][2] // 2,  # 中心点x
         boxes[i][1] + boxes[i][3] // 2,  # 中心点y
         round(confs[i], 2)]
        for i in indices.flatten()
    ] if len(indices) > 0 else []
    return result


if __name__ == "__main__":
    while True:
        print(detect_camera())
