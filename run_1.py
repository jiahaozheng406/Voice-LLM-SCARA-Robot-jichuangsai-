from detect_new1 import detect_camera
from scara_1 import SCARAController
import time

def return_to_home_position(arm):
    """返回复位位置"""
    try:
        print("尝试返回复位位置...")
        if not arm.move_position(x=0, y=0, z=100, phi=0, gripper=0):
            print("返回复位位置失败，尝试二次移动")
            arm.move_position(x=0, y=0, z=100, phi=0, gripper=0)
        print("已回到复位位置")
        return True
    except Exception as e:
        print(f"返回复位位置出错：{e}")
        return False

def pick_and_place(arm, obj_x, obj_y, drop_x, drop_y, drop_z=35):
    """分步执行抓取-放置流程"""
    try:
        # 1. 移动到物体上方安全高度
        if not arm.move_position(x=obj_x, y=obj_y, z=100):
            return False
        print("步骤1：已移动到物体上方")

        # 2. 张开夹爪
        if not arm.move_position(x=obj_x, y=obj_y, gripper=0):
            return False
        print("步骤2：夹爪已张开")

        # 3. 下降到抓取位置
        if not arm.move_position(x=obj_x, y=obj_y, z=0, gripper=0):
            return False
        print("步骤3：已下降到抓取高度")

        # 4. 闭合夹爪（抓取）
        if not arm.move_position(x=obj_x, y=obj_y, z=0, gripper=105):
            return False
        print("步骤4：夹爪已闭合（抓取成功）")

        # 5. 提升到安全高度
        if not arm.move_position(x=obj_x, y=obj_y, z=100, gripper=105):
            return False
        print("步骤5：已提升到安全高度")

        # 6. 移动到过渡点
        time.sleep(0.5)
        print("步骤6：已到达过渡点")

        # 7. 移动到放置位置上方
        if not arm.move_position(x=drop_x, y=drop_y, z=100, gripper=105):
            return False
        print("步骤7：已到达放置位置上方")

        # 8. 下降到放置高度
        if not arm.move_position(x=drop_x, y=drop_y, z=drop_z, gripper=0):
            return False
        print("步骤8：已下降到放置高度")

        # 9. 张开夹爪（释放）
        if not arm.move_position(x=drop_x, y=drop_y, z=drop_z, gripper=0):
            return False
        print("步骤9：夹爪已张开（放置成功）")

        # 10. 返回初始位置
        if not arm.move_position(x=384.5, y=0, z=100):
            return False
        print("步骤10：已返回初始位置")
        time.sleep(0.2)

        return True
    except Exception as e:
        print(f"运动步骤出错：{e}")
        return_to_home_position(arm)
        return False

def run(handler):
    """自动清理主循环（不可被打断，连续3次无物体则退出）"""
    arm = None
    try:
        arm = SCARAController("/dev/ttyACM0", 115200, debug_mode=True)
        print("正在复位机械臂...")
        if not arm.home(timeout=60):
            print("复位失败，退出")
            arm.close()
            handler.current_command = None  # 清除指令标记
            return
        print("机械臂复位完成")

        drop_locations = {
            'eraser': (115, -80, 50),
            'pen': (115, -80, 50),
            'sharpener': (115, -90, 50),
            'paper': (-260, 180, 50)
        }

        no_object_count = 0  # 连续无物体计数器
        MAX_NO_OBJECT = 2   # 最大连续无物体次数

        while True:
            # 检查连续无物体次数
            if no_object_count >= MAX_NO_OBJECT:
                print(f"连续{MAX_NO_OBJECT}次未检测到物体，退出自动清理")
                break

            try:
                data = detect_camera()
                print(f"检测到 {len(data)} 个物体")

                if not data:
                    no_object_count += 1
                    print(f"未检测到物体（{no_object_count}/{MAX_NO_OBJECT}）")
                    time.sleep(1)  # 等待1秒后重试
                    continue
                else:
                    no_object_count = 0  # 检测到物体，重置计数器

                for obj in data:
                    classes = obj[0]
                    a, b = obj[1], obj[2]

                    # 坐标转换
                    a = int(0.357 * a - 104)
                    b = int(374 - 0.357 * b)
                    print(f"处理 {classes}，坐标: ({a}, {b})")

                    if classes in drop_locations:
                        drop_x, drop_y, drop_z = drop_locations[classes]
                        if pick_and_place(arm, a, b, drop_x, drop_y, drop_z):
                            print(f"{classes} 抓取放置完成")
                        else:
                            print(f"{classes} 抓取放置失败，尝试回到复位位置")
                            return_to_home_position(arm)
                            time.sleep(1)
                            break
                    else:
                        print(f"未知物体: {classes}")

                time.sleep(0.1)
            except Exception as e:
                print(f"主循环出错：{e}")
                return_to_home_position(arm)
                time.sleep(1)

    except Exception as e:
        print(f"初始化错误: {e}")
    finally:
        if arm and arm.is_connected():
            arm.close()
            print("连接关闭")
        # 清除指令标记，允许新指令执行
        handler.current_command = None
        print("自动清理已退出")

if __name__ == "__main__":
    run(object())  # 保持单独运行能力
