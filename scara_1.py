import serial
import math
import time


class SCARAController:
    def __init__(self, port, baudrate=115200, debug_mode=False):
        self.L1 = 228.0  # 大臂长度
        self.L2 = 156.5
        # 当前状态（用于单步运动的默认值）
        self.current_theta1 = 0
        self.current_theta2 = 0
        self.current_phi = 0
        self.current_z = 100
        self.current_gripper = 0

        # 串口初始化
        self.ser = None
        self.debug_mode = debug_mode
        try:
            self.ser = serial.Serial(port, baudrate, timeout=0.1)
            time.sleep(2)
            self.ser.reset_input_buffer()
            print(f"已连接到 {port}")
        except Exception as e:
            print(f"连接失败: {e}")
            self.ser = None

    def _read_serial(self):
        """读取串口数据并返回"""
        if self.ser.in_waiting:
            return self.ser.readline().decode('ASCII', errors='replace').strip()
        return ""

    def is_connected(self):
        return self.ser and self.ser.is_open

    def send_cmd(self, cmd_id, params=None, timeout=10):
        if not self.is_connected():
            print("未连接到设备")
            return False

        params = [int(p) if p is not None else 0 for p in (params or [])]
        cmd = [cmd_id] + params + [0] * (9 - len(params))
        cmd_str = ",".join(map(str, cmd))

        print(f"发送的数据: {cmd}")

        # 发送前清空接收缓冲区，避免残留数据干扰
        self.ser.reset_input_buffer()

        # 发送指令
        self.ser.write((cmd_str + "\n").encode('ASCII'))

        while True:
            line = self.ser.readline().decode().strip()
            if line == "DONE":
                print(f"{line}")
                return True

    def home(self, speed=5000, accel=3000, max_retries=5, timeout=60):
        return self.send_cmd(1, [0, 0, 0, 0, 0, 0, speed, accel], timeout=timeout)

    def move_joints(self, theta1, theta2, phi, z, gripper, speed=5000, accel=3000, max_retries=5):
        params = [0, int(theta1), int(theta2), int(phi), int(z), int(gripper), int(speed), int(accel)]
        return self.send_cmd(2, params, timeout=30)

    def inverse_kinematics(self, x, y):
        """计算逆运动学（返回整数角度）"""
        x, y = int(x), int(y)  # 确保输入为整数
        r = math.hypot(x, y)
        # 检查工作范围
        if not (abs(int(self.L1) - int(self.L2)) <= r <= int(self.L1) + int(self.L2)):
            raise ValueError(f"目标点超出范围 (r={int(r)})")

        # 计算角度（肘部向下）
        cos_theta2 = (r ** 2 - self.L1 ** 2 - self.L2 ** 2) / (2 * self.L1 * self.L2)
        cos_theta2 = max(min(cos_theta2, 1), -1)  # 限制范围
        theta2 = math.acos(cos_theta2)
        theta1 = math.atan2(y, x) - math.atan2(self.L2 * math.sin(theta2), self.L1 + self.L2 * cos_theta2)

        return math.degrees(theta1), math.degrees(theta2)

    def move_position(self, x, y, z=None, phi=None, gripper=None, speed=5000, accel=3000):
        """通过笛卡尔坐标运动（内部转换为关节角度）"""
        z = z if z is not None else self.current_z
        phi = phi if phi is not None else self.current_phi
        gripper = gripper if gripper is not None else self.current_gripper

        # 逆运动学计算（转换x,y到theta1,theta2）
        theta1, theta2 = self.inverse_kinematics(x, y)
        return self.move_joints(theta1, theta2, phi, z, gripper, speed, accel)

    def close(self):
        """关闭连接"""
        if self.is_connected():
            self.ser.close()
            print("连接已关闭")