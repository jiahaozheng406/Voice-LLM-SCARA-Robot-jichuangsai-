import serial
import time
from detect_new1 import detect_camera
from run_1 import run, return_to_home_position
from scara_1 import SCARAController


class DualSerialHandler:
    def __init__(self):
        # 串口配置 按照自己的串口来设置
        self.arm_serial_port = "/dev/ttyCH341USB0"
        self.cmd_serial_port = "/dev/ttyCH341USB1"
        self.baudrate = 115200

        # 状态管理
        self.arm = None
        self.cmd_serial = None
        self.running = False  # run循环运行标志
        self.last_command_time = time.time()
        self.COMMAND_TIMEOUT = 180  # 超时时间（秒）
        self.current_command = None  # 当前执行的指令（仅用于状态标记）
        self.allow_interrupt = False  # 全局中断允许标志（始终为False）

    def connect_arm(self):
        """连接机械臂"""
        if self.arm and self.arm.is_connected():
            return True
        try:
            self.arm = SCARAController(
                port=self.arm_serial_port,
                baudrate=self.baudrate,
                debug_mode=True
            )
            print(f"机械臂已连接到 {self.arm_serial_port}")
            return True
        except Exception as e:
            print(f"机械臂连接失败: {e}")
            self.arm = None
            return False

    def start_run_loop(self):
        """启动run循环（不可被打断）"""
        self.running = True
        print("启动run循环（不可被打断）")
        run(self)  # 传入自身实例用于状态检查

    def pick_specific_object(self, target):
        """抓取指定物体（不可被打断）"""
        print(f"开始抓取 {target}...")
        try:
            # 步骤1：获取检测结果
            detection_result = detect_camera()
            if not detection_result:
                print(f"未检测到任何物体，无法抓取{target}")
                return False

            # 步骤2：查找目标物体
            target_info = next((obj for obj in detection_result if obj[0] == target), None)
            if not target_info:
                print(f"未检测到{target}")
                return False

            # 步骤3：坐标转换
            _, obj_x, obj_y, _ = target_info
            converted_x = int(0.357 * obj_x - 104)
            converted_y = int(374 - 0.357 * obj_y)
            print(f"{target}坐标转换后: ({converted_x}, {converted_y})")

            # 步骤4：执行抓取放置（全程不检查中断）
            drop_locations = {
                'pen': (115, -80, 50),
                'eraser': (115, -80, 50),
                'sharpener': (115, -80, 50),
                'paper': (-260, 180, 70)
            }
            drop_x, drop_y, drop_z = drop_locations[target]

            # 移动到物体上方
            if not self.arm.move_position(x=converted_x, y=converted_y, z=100):
                return False
            print("步骤1：已移动到物体上方")

            # 张开夹爪
            if not self.arm.move_position(x=converted_x, y=converted_y, z=100,gripper=0):
                return False
            print("步骤2：夹爪已张开")

            # 下降到抓取高度
            if not self.arm.move_position(x=converted_x, y=converted_y, z=0,gripper=0):
                return False
            print("步骤3：已下降到抓取高度")

            # 闭合夹爪
            if not self.arm.move_position(x=converted_x, y=converted_y, z=0,gripper=105):
                return False
            print("步骤4：夹爪已闭合（抓取成功）")

            # 提升到安全高度
            if not self.arm.move_position(x=converted_x, y=converted_y, z=100,gripper=105):
                return False
            print("步骤5：已提升到安全高度")

            # 移动到放置位置上方
            if not self.arm.move_position(x=drop_x, y=drop_y,z=100,gripper=105):
                return False
            print("步骤6：已到达放置位置上方")

            # 下降到放置高度
            if not self.arm.move_position(x=drop_x, y=drop_y,z=drop_z):
                return False
            print("步骤7：已下降到放置高度")

            # 张开夹爪释放
            if not self.arm.move_position(x=drop_x, y=drop_y,z=drop_z,gripper=0):
                return False
            print("步骤8：夹爪已张开（放置成功）")

            # 返回初始位置
            if not self.arm.move_position(x=384.5, y=0, z=100):
                return False
            print("步骤9：已返回初始位置")

            print(f"{target}抓取放置完成")
            return True

        except Exception as e:
            print(f"抓取{target}出错: {e}")
            return_to_home_position(self.arm)
            return False

    def handle_new_command(self, cmd,keyword=None):
        """处理新指令（仅在当前无操作时执行）"""
        cmd = cmd.strip().lower()if cmd else '111'
        # 若当前有正在执行的指令（除None外），则忽略新指令
        if self.current_command is not None:
            print(f"\n当前有正在执行的指令{self.current_command}，忽略新指令: {cmd}")
            return


        # 多输入归一化
        if keyword is not None:
            if "复位" in keyword or cmd == "a":
                cmd = "a"
            if "全面清理" in keyword or cmd == "b":
                cmd = "b"
            elif "笔" in keyword or cmd == "c":
                cmd = "c"
            elif "橡皮" in keyword or cmd == "d":
                cmd = "d"
            elif "削笔刀" in keyword or cmd == "e":
                cmd = "e"
            elif "纸" in keyword or cmd == "f":
                cmd = "f"
        if cmd == '111':
            print(f"默认无效指令: {cmd}，不执行任何操作")
            return

        print(f"\n收到新指令: {cmd}，开始执行...")
        self.last_command_time = time.time()
        self.current_command = cmd  # 标记当前指令，防止被打断

        # 确保机械臂连接
        if cmd in ['b', 'c', 'd', 'e', 'f'] and not self.connect_arm():
            print("机械臂未连接，无法执行指令")
            self.current_command = None
            return

        # 执行指令（全程不被打断）
        try:
            if cmd == 'a':
                # 复位机械臂
                print("执行复位指令...")
                if self.arm:
                    if self.arm.home(timeout=60):
                        print("机械臂复位完成")
                    else:
                        print("复位失败")
                else:
                    print("尝试连接机械臂并复位...")
                    if self.connect_arm():
                        self.arm.home(timeout=60)

            elif cmd == 'b':
                # 启动自动清理
                print("执行自动清理...")
                self.start_run_loop()

            elif cmd == 'c':
                # 抓取pen
                self.pick_specific_object("pen")

            elif cmd == 'd':
                # 抓取eraser
                self.pick_specific_object("eraser")

            elif cmd == 'e':
                # 抓取sharpener
                self.pick_specific_object("sharpener")

            elif cmd == 'f':
                # 抓取paper
                self.pick_specific_object("paper")

            else:
                print(f"无效指令: {cmd}，请发送a-f")

        except Exception as e:
            print(f"执行指令{cmd}出错: {e}")
            return_to_home_position(self.arm)
        finally:
            self.current_command = None  # 指令执行完毕，清除标记

    def start(self):
        """启动主程序"""
        try:
            self.cmd_serial = serial.Serial(
                port=self.cmd_serial_port,
                baudrate=self.baudrate,
                timeout=0.1,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
            print(f"指令接收串口已连接到 {self.cmd_serial_port}")
            print(f"无指令{self.COMMAND_TIMEOUT}秒后将自动启动清理...")

            while True:
                # 超时检查（自动启动清理）
                idle_time = time.time() - self.last_command_time
                if idle_time >= self.COMMAND_TIMEOUT:
                    # 仅当当前无操作时才启动超时清理
                    if self.current_command is None:
                        print(f"已超过{self.COMMAND_TIMEOUT}秒无指令，自动启动清理...")
                        self.handle_new_command(cmd='b')  # 触发自动清理

                # 检查指令接收
                if self.cmd_serial.in_waiting > 0:
                    cmd1 = self.cmd_serial.readline().decode('utf-8', errors='ignore').strip()
                    if len(cmd1) == 1 and cmd1 in ['a', 'b', 'c', 'd', 'e', 'f']:
                        self.handle_new_command(cmd=cmd1)
                    else:
                        print(f"无效指令格式: {cmd1}，请发送单个字符(a-f)")

                time.sleep(0.05)

        except serial.SerialException as e:
            print(f"串口错误: {e}")
        except KeyboardInterrupt:
            print("\n用户中断程序")
        finally:
            if self.cmd_serial and self.cmd_serial.is_open:
                self.cmd_serial.close()
                print("指令接收串口已关闭")
            if self.arm and self.arm.is_connected():
                self.arm.close()
                print("机械臂连接已关闭")


if __name__ == "__main__":
    handler = DualSerialHandler()
    handler.start()
