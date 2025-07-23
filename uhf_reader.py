import time
import threading
import serial.tools.list_ports
from uhf.reader import GClient, getUsbHidPathList, EnumG, MsgBaseInventoryEpc, MsgBaseStop, ParamEpcReadTid


class UHFReader:
    """管理RFID读写器操作的类"""

    def __init__(self, app):
        self.app = app
        self.g_client = GClient()
        self.scanning = False
        self.stop_event = threading.Event()
        self.connected = False
        self.scan_thread = None

    def get_available_com_ports(self):
        """获取可用的COM端口列表"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]

    def auto_connect(self):
        """尝试自动连接设备"""
        self.connect_usb()

    def connect_device(self, connection_type, com_port, baud_rate):
        """连接设备"""
        if self.connected:
            self.app.log_message("设备已连接")
            return

        if connection_type == "USB":
            self.connect_usb()
        elif connection_type == "串口(RS232)":
            self.connect_serial(com_port, baud_rate)
        else:
            self.app.log_message("错误: 未知的连接类型")

    def disconnect_device(self):
        """断开设备连接"""
        if self.scanning:
            self.stop_scanning()

        if self.connected:
            try:
                self.g_client.close()
                self.connected = False
                self.app.ui_queue.put(("update_ui", "status", "状态: 未连接"))
                self.app.log_message("设备已断开连接")
                self.app.ui_queue.put(("update_ui", "button_state", "connect_btn", "normal"))
                self.app.ui_queue.put(("update_ui", "button_state", "disconnect_btn", "disabled"))
                self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "disabled"))
            except Exception as e:
                self.app.log_message(f"断开连接时出错: {str(e)}")

    def connect_usb(self):
        """连接USB设备"""
        path_list = getUsbHidPathList()
        if path_list:
            try:
                if self.g_client.openUsbHid(path_list[0]):
                    self.connected = True
                    self.app.ui_queue.put(("update_ui", "status", "状态: 已连接(USB)"))
                    self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "normal"))
                    self.app.ui_queue.put(("update_ui", "button_state", "disconnect_btn", "normal"))
                    self.app.ui_queue.put(("update_ui", "button_state", "connect_btn", "disabled"))
                    self.app.log_message("USB设备连接成功")
                    return
            except Exception as e:
                self.app.log_message(f"USB连接错误: {str(e)}")

        self.connected = False
        self.app.ui_queue.put(("update_ui", "status", "状态: 未连接"))
        self.app.log_message("未检测到USB RFID设备，请检查连接")
        self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "disabled"))

    def connect_serial(self, com_port, baud_rate):
        """连接串口设备"""
        if not com_port:
            self.app.log_message("错误: 请选择COM端口")
            return

        try:
            baud = int(baud_rate)
        except ValueError:
            self.app.log_message(f"错误: 无效的波特率: {baud_rate}")
            return

        try:
            if self.g_client.openSerial((com_port, baud)):
                self.connected = True
                self.app.ui_queue.put(("update_ui", "status", f"状态: 已连接({com_port})"))
                self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "normal"))
                self.app.ui_queue.put(("update_ui", "button_state", "disconnect_btn", "normal"))
                self.app.ui_queue.put(("update_ui", "button_state", "connect_btn", "disabled"))
                self.app.log_message(f"串口设备连接成功: {com_port}@{baud}bps")
                return
        except Exception as e:
            self.app.log_message(f"串口连接错误: {str(e)}")

        self.connected = False
        self.app.ui_queue.put(("update_ui", "status", "状态: 未连接"))
        self.app.log_message(f"无法连接串口设备: {com_port}")
        self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "disabled"))

    def start_scanning(self):
        """开始扫描RFID标签"""
        if not self.connected:
            self.app.log_message("错误: 未连接到设备")
            return

        self.scanning = True
        self.stop_event.clear()
        self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "disabled"))
        self.app.ui_queue.put(("update_ui", "button_state", "stop_btn", "normal"))
        self.app.log_message(f"开始{self.app.inventory_mode.get()}扫描...")

        # 设置回调函数
        self.g_client.callEpcInfo = self.received_epc
        self.g_client.callEpcOver = self.received_epc_over

        # 在单独线程中运行扫描
        self.scan_thread = threading.Thread(target=self.run_scan, daemon=True)
        self.scan_thread.start()

    def stop_scanning(self):
        """停止扫描"""
        self.scanning = False
        self.app.ui_queue.put(("update_ui", "button_state", "stop_btn", "disabled"))
        self.app.ui_queue.put(("update_ui", "button_state", "start_btn", "normal"))
        self.app.log_message("停止扫描...")
        self.stop_event.set()

    def received_epc(self, epcInfo):
        """处理接收到的EPC标签信息"""
        if epcInfo.result == 0 and epcInfo.tid:
            tid_str = epcInfo.tid
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            self.app.ui_queue.put(("tid", tid_str, timestamp))

    def received_epc_over(self, epcOver):
        """EPC扫描结束回调"""
        self.app.log_message("扫描周期完成")

    def run_scan(self):
        """运行扫描的线程函数"""
        while self.scanning and not self.stop_event.is_set():
            try:
                # 使用默认配置
                antenna_value = EnumG.AntennaNo_1.value

                msg = MsgBaseInventoryEpc(
                    antennaEnable=antenna_value,
                    inventoryMode=EnumG.InventoryMode_Inventory.value
                )

                tid_param = ParamEpcReadTid(
                    mode=EnumG.ParamTidMode_Auto.value,
                    dataLen=6  # 默认TID长度
                )
                msg.readTid = tid_param

                if self.g_client.sendSynMsg(msg) != 0:
                    self.app.log_message(f"扫描错误: {msg.rtMsg}")

                time.sleep(0.2)  # 降低CPU使用率
            except Exception as e:
                self.app.log_message(f"扫描异常: {str(e)}")
                break

        try:
            stop_msg = MsgBaseStop()
            if self.g_client.sendSynMsg(stop_msg) == 0:
                self.app.log_message("扫描已停止")
            else:
                self.app.log_message(f"停止扫描时出错: {stop_msg.rtMsg}")
        except Exception as e:
            self.app.log_message(f"停止扫描时出错: {str(e)}")

    def on_closing(self):
        """关闭窗口时清理资源"""
        self.stop_scanning()
        if self.connected:
            try:
                self.g_client.close()
            except:
                pass