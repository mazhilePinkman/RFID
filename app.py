import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, StringVar, simpledialog
import time
import os
import threading
import queue
from uhf_reader import UHFReader
import requests
import config  # 导入配置

class RFIDScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RFID扫描器")
        self.root.geometry("1100x650")
        self.root.resizable(True, True)

        # 退出登录按钮
        self.authorization = None
        
        # 创建读写器客户端
        self.uhf_reader = UHFReader(self)
        self.scanning = False
        self.connected = False

        # 用于跟踪TID出现次数的字典
        self.tid_counts = {}
        self.tid_to_id = {}  # TID到编号的映射
        self.total_scans = 0
        self.next_id = 1  # 下一个可用编号

        # 盘点模式（入库/出库/录入）
        self.inventory_mode = StringVar(value="入库")

        # 管道类型
        self.pipe_types = ["请稍候..."]  # 初始值
        self.selected_pipe_type = StringVar()
        self.selected_pipe_type.set("请稍候...")

        # UI更新队列
        self.ui_queue = queue.Queue()

        # 创建UI
        self.create_widgets()

        # 启动UI更新任务
        self.root.after(100, self.process_ui_queue)

        # 尝试自动连接设备
        self.uhf_reader.auto_connect()

        # 启动管道类型获取
        self.fetch_pipe_types()

    def show_login_dialog(self):
        LoginDialog(self.root, self)

    def on_closing(self):
        self.root.destroy()

    def create_widgets(self):
        """创建应用程序界面"""
        # 主布局框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 连接设置区域
        self.create_connection_frame(main_frame)

        # 顶部控制按钮区域
        self.create_control_frame(main_frame)

        # 标签计数表格框架
        self.create_table_frame(main_frame)

        # 操作日志区域
        self.create_log_frame(main_frame)

        # 底部统计信息
        self.create_footer_frame(main_frame)
        self.create_location_frame(main_frame)
    def create_connection_frame(self, parent):
        """创建连接设置区域"""
        connection_frame = ttk.LabelFrame(parent, text="连接设置", padding="5")
        connection_frame.pack(fill=tk.X, pady=(0, 10))

        # 连接类型选择
        ttk.Label(connection_frame, text="连接类型:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.connection_type = StringVar(value="USB")
        connection_types = ["USB", "串口(RS232)"]
        ttk.Combobox(connection_frame, textvariable=self.connection_type, values=connection_types,
                     state="readonly", width=15).grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 串口设置区域
        self.serial_frame = ttk.Frame(connection_frame)
        self.serial_frame.grid(row=0, column=2, columnspan=3, padx=5, pady=5, sticky="w")

        # COM端口选择
        ttk.Label(self.serial_frame, text="COM端口:").grid(row=0, column=0, padx=5, sticky="e")
        self.com_port = StringVar()
        self.com_ports = self.uhf_reader.get_available_com_ports()
        self.combo_com = ttk.Combobox(self.serial_frame, textvariable=self.com_port, values=self.com_ports, width=8)
        self.combo_com.grid(row=0, column=1, padx=5, sticky="w")
        if self.com_ports:
            self.combo_com.current(0)

        # 刷新COM端口按钮
        ttk.Button(self.serial_frame, text="刷新", command=self.refresh_com_ports, width=6).grid(row=0, column=4,
                                                                                                 padx=5)

        # 波特率选择
        ttk.Label(self.serial_frame, text="波特率:").grid(row=0, column=2, padx=5, sticky="e")
        self.baud_rate = StringVar(value="115200")
        baud_rates = ["9600", "19200", "38400", "57600", "115200"]
        ttk.Combobox(self.serial_frame, textvariable=self.baud_rate, values=baud_rates, width=8).grid(row=0, column=3,
                                                                                                      padx=5,
                                                                                                      sticky="w")

        # 连接按钮
        self.connect_btn = ttk.Button(connection_frame, text="连接设备", command=self.connect_device)
        self.connect_btn.grid(row=0, column=5, padx=10, sticky="e")

        # 断开连接按钮
        self.disconnect_btn = ttk.Button(connection_frame, text="断开连接", command=self.disconnect_device,
                                         state=tk.DISABLED)
        self.disconnect_btn.grid(row=0, column=6, padx=10, sticky="e")

        # 登录按钮
        self.login_button = tk.Button(connection_frame, text="登录", command=self.show_login_dialog)
        self.login_button.grid(row=0, column=7, padx=10, sticky="e")

        # 更新串口设置区域可见性
        self.update_connection_ui()
        self.connection_type.trace("w", lambda *args: self.update_connection_ui())

        self.logout_button = tk.Button(connection_frame, text="退出登录", command=self.logout, state=tk.DISABLED)
        self.logout_button.grid(row=0, column=8, padx=10, sticky="e")

    def create_control_frame(self, parent):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = ttk.Button(control_frame, text="开始扫描", command=self.start_scanning)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(control_frame, text="停止扫描", command=self.stop_scanning, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(control_frame, text="清除所有数据", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 在现有控制区域添加全选按钮
        self.select_all_var = tk.BooleanVar()
        self.select_all_btn = ttk.Checkbutton(control_frame, text="全选",
                                              variable=self.select_all_var,
                                              command=self.toggle_select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=5)

        # 添加盘点模式选择
        ttk.Label(control_frame, text="盘点模式:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(control_frame, text="入库", variable=self.inventory_mode, value="入库").pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Radiobutton(control_frame, text="出库", variable=self.inventory_mode, value="出库").pack(side=tk.LEFT,
                                                                                                     padx=5)
        ttk.Radiobutton(control_frame, text="录入", variable=self.inventory_mode, value="录入").pack(side=tk.LEFT,
                                                                                                     padx=5)

        # 管道类型选择
        ttk.Label(control_frame, text="管道参数:").pack(side=tk.LEFT, padx=(10, 5))
        self.pipe_type_combo = ttk.Combobox(control_frame,
                                            textvariable=self.selected_pipe_type,
                                            values=self.pipe_types,
                                            state="readonly",
                                            width=15)
        self.pipe_type_combo.pack(side=tk.LEFT, padx=5)

        # 上传按钮
        self.upload_btn = ttk.Button(control_frame, text="上传", command=self.upload_to_server, state=tk.DISABLED)
        self.upload_btn.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.status_var = tk.StringVar(value="状态: 未连接")
        status_label = ttk.Label(control_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=10)

        # 绑定盘点模式变更事件
        self.inventory_mode.trace("w", self.on_inventory_mode_change)

    def create_table_frame(self, parent):
        """创建标签计数表格区域"""
        table_frame = ttk.LabelFrame(parent, text="TID", padding="5")
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 创建表格来显示TID和计数
        self.tree = ttk.Treeview(table_frame,
                                 columns=("select", "id", "tid", "formatted_tid", "count", "last_time"),
                                 show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 配置表格列
        self.tree.heading("select", text="选择")
        self.tree.column("select", width=20, anchor=tk.CENTER)
        self.tree.heading("id", text="编号")
        self.tree.column("id", width=50, anchor=tk.CENTER, stretch=tk.NO)
        self.tree.heading("tid", text="TID")
        self.tree.column("tid", width=170, stretch=tk.YES, anchor=tk.CENTER)
        self.tree.heading("formatted_tid", text="格式化TID", anchor=tk.CENTER)
        self.tree.column("formatted_tid", width=250, anchor=tk.CENTER)
        self.tree.heading("count", text="出现次数")
        self.tree.column("count", width=80, anchor=tk.CENTER)
        self.tree.heading("last_time", text="最后扫描时间")
        self.tree.column("last_time", width=150, anchor=tk.CENTER)
        self.tree.bind('<Button-1>', self.on_tree_click)

    def create_log_frame(self, parent):
        """创建操作日志区域"""
        log_frame = ttk.LabelFrame(parent, text="操作日志", padding="5")
        log_frame.pack(fill=tk.X, pady=(10, 0))

        self.log_area = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=5, font=("Consolas", 9))
        self.log_area.pack(fill=tk.BOTH)
        self.log_area.config(state=tk.DISABLED)

    def create_footer_frame(self, parent):
        """创建底部统计信息区域"""
        footer_frame = ttk.Frame(parent)
        footer_frame.pack(fill=tk.X, pady=(10, 0))

        self.total_var = tk.StringVar(value="总扫描次数: 0")
        total_label = ttk.Label(footer_frame, textvariable=self.total_var)
        total_label.pack(side=tk.LEFT, padx=10)

        self.unique_var = tk.StringVar(value="唯一标签数: 0")
        unique_label = ttk.Label(footer_frame, textvariable=self.unique_var)
        unique_label.pack(side=tk.LEFT, padx=10)

        self.timestamp_var = tk.StringVar(value="最后扫描时间: -")
        timestamp_label = ttk.Label(footer_frame, textvariable=self.timestamp_var)
        timestamp_label.pack(side=tk.RIGHT, padx=10)

    def refresh_com_ports(self):
        """刷新COM端口列表"""
        self.com_ports = self.uhf_reader.get_available_com_ports()
        self.combo_com['values'] = self.com_ports
        if self.com_ports:
            self.combo_com.current(0)
        self.log_message("已刷新COM端口列表")

    def update_connection_ui(self):
        """根据选择的连接类型更新UI"""
        if self.connection_type.get() == "串口(RS232)":
            self.serial_frame.grid()
        else:
            self.serial_frame.grid_remove()

    def connect_device(self):
        """连接设备"""
        self.uhf_reader.connect_device(
            self.connection_type.get(),
            self.com_port.get(),
            self.baud_rate.get()
        )

    def disconnect_device(self):
        """断开设备连接"""
        self.uhf_reader.disconnect_device()

    def start_scanning(self):
        """开始扫描RFID标签"""
        self.uhf_reader.start_scanning()

    def stop_scanning(self):
        """停止扫描"""
        self.uhf_reader.stop_scanning()

    def clear_all(self):
        """清除所有数据"""
        if messagebox.askyesno("确认", "确定要清除所有数据吗？"):
            self.tree.delete(*self.tree.get_children())

            self.log_area.config(state=tk.NORMAL)
            self.log_area.delete(1.0, tk.END)
            self.log_area.config(state=tk.DISABLED)
            self.log_message("已清除所有数据")

            self.tid_counts = {}
            self.tid_to_id = {}
            self.total_scans = 0
            self.next_id = 1
            self.total_var.set("总扫描次数: 0")
            self.unique_var.set("唯一标签数: 0")
            self.timestamp_var.set("最后扫描时间: -")

            self.upload_btn.config(state=tk.DISABLED)

    def log_message(self, message):
        """在日志区域添加消息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.ui_queue.put(("log", formatted_message))

    def process_ui_queue(self):
        """处理UI更新队列"""
        try:
            while not self.ui_queue.empty():
                task = self.ui_queue.get_nowait()
                if task[0] == "location":
                    # 更新经纬度显示
                    self.longitude_var.set(f"经度: {task[1]['longitude']}")
                    self.latitude_var.set(f"纬度: {task[1]['latitude']}")
                elif task[0] == "log":
                    self._add_log_message(task[1])
                elif task[0] == "tid":
                    self._update_ui_with_tid(task[1], task[2])
                elif task[0] == "messagebox":
                    if task[3] == "info":
                        messagebox.showinfo(task[1], task[2])
                    else:
                        messagebox.showerror(task[1], task[2])
                elif task[0] == "enable_upload":
                    self.upload_btn.config(state=tk.NORMAL, text="上传")
                elif task[0] == "update_pipe_types":
                    self.pipe_types = task[1]
                    self.pipe_type_combo['values'] = self.pipe_types
                    if self.pipe_types:
                        self.selected_pipe_type.set(self.pipe_types[0])
                    self.update_pipe_type_state()
                elif task[0] == "update_ui":
                    # 通用UI更新
                    if task[1] == "status":
                        self.status_var.set(task[2])
                    elif task[1] == "button_state":
                        btn = getattr(self, task[2])
                        # 支持单独设置state或text
                        if len(task) > 5 and task[5] == "text":
                            btn.config(text=task[3])
                        elif len(task) > 4 and task[4] == "text":
                            btn.config(text=task[3])
                        else:
                            btn.config(state=task[3])
        except queue.Empty:
            pass

        self.root.after(100, self.process_ui_queue)

    def _add_log_message(self, message):
        """实际添加日志消息到UI"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.config(state=tk.DISABLED)

    def _update_ui_with_tid(self, tid, timestamp):
        """实际更新UI显示新的TID标签"""
        self.total_scans += 1
        self.total_var.set(f"总扫描次数: {self.total_scans}")
        self.timestamp_var.set(f"最后扫描时间: {timestamp}")

        formatted_tid = ' '.join(tid[i:i + 4] for i in range(0, len(tid), 4))

        if tid in self.tid_to_id:
            # 已有TID，更新计数
            self.tid_counts[tid]["count"] += 1
            self.tid_counts[tid]["last_time"] = timestamp
            current_id = self.tid_to_id[tid]

            # 更新表格
            for item in self.tree.get_children():
                item_values = self.tree.item(item, "values")
                if len(item_values) >= 2 and item_values[1] == tid:
                    self.tree.item(item, values=(
                        current_id,
                        tid,
                        formatted_tid,
                        self.tid_counts[tid]["count"],
                        timestamp
                    ))
                    self.tree.see(item)
                    break
        else:
            # 新TID
            current_id = self.next_id
            self.next_id += 1
            self.tid_to_id[tid] = current_id
            self.tid_counts[tid] = {
                "id": current_id,
                "count": 1,
                "last_time": timestamp
            }

            # 插入新行
            self.tree.insert("", "end", values=(
                current_id,
                tid,
                formatted_tid,
                1,
                timestamp
            ))

            self.unique_var.set(f"唯一标签数: {len(self.tid_counts)}")
            self.upload_btn.config(state=tk.NORMAL)

        # 添加日志
        self._add_log_message(f"检测到标签TID: {formatted_tid} (编号: {current_id})")

    def upload_to_server(self):
        """上传数据到服务器"""
        from server_upload import upload_to_server
        upload_to_server(self)

    def fetch_pipe_types(self):
        """获取管道类型列表"""
        from server_upload import fetch_pipe_params
        fetch_thread = threading.Thread(target=fetch_pipe_params, args=(self,))
        fetch_thread.daemon = True
        fetch_thread.start()

    def on_inventory_mode_change(self, *args):
        """盘点模式变更处理"""
        self.update_pipe_type_state()

        # 录入模式下自动刷新管道类型
        if self.inventory_mode.get() == "录入":
            self.fetch_pipe_types()

    def update_pipe_type_state(self):
        """更新管道类型选择框状态"""
        if self.inventory_mode.get() == "录入":
            self.pipe_type_combo.config(state="readonly")
        else:
            self.pipe_type_combo.config(state="disabled")

    def logout(self):
        self.authorization = None
        messagebox.showinfo("退出登录", "已退出登录")
        self.logout_button.config(state=tk.DISABLED)
        self.login_button.config(state=tk.NORMAL)

    def on_closing(self):
        """关闭窗口时清理资源"""
        self.uhf_reader.on_closing()
        self.root.destroy()

    def on_tree_click(self, event):
        """处理表格点击事件"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1":  # 选择列
                item = self.tree.identify_row(event.y)
                if item:
                    values = list(self.tree.item(item)['values'])
                    values[0] = "√" if values[0] != "√" else ""
                    self.tree.item(item, values=values)

                    # 检查是否全选
                    all_selected = all(
                        self.tree.item(child)['values'][0] == "√"
                        for child in self.tree.get_children()
                    )
                    self.select_all_var.set(all_selected)

    def toggle_select_all(self):
        """全选/取消全选"""
        state = self.select_all_var.get()
        for item in self.tree.get_children():
            values = list(self.tree.item(item)['values'])
            values[0] = "√" if state else ""
            self.tree.item(item, values=values)

    def _update_ui_with_tid(self, tid, timestamp):
        # 修改添加新TID的方法
        if tid in self.tid_to_id:
            # 更新现有TID
            for item in self.tree.get_children():
                item_values = self.tree.item(item, "values")
                if len(item_values) >= 3 and item_values[2] == tid:
                    new_values = list(item_values)
                    new_values[4] = self.tid_counts[tid]["count"]
                    new_values[5] = timestamp
                    self.tree.item(item, values=new_values)
                    self.tree.see(item)
                    break
        else:
            # 添加新TID
            current_id = self.next_id
            self.next_id += 1
            self.tid_to_id[tid] = current_id
            self.tid_counts[tid] = {
                "id": current_id,
                "count": 1,
                "last_time": timestamp
            }

            formatted_tid = ' '.join(tid[i:i + 4] for i in range(0, len(tid), 4))
            self.tree.insert("", "end", values=(
                "",  # 选择状态
                current_id,
                tid,
                formatted_tid,
                1,
                timestamp
            ))

    def create_location_frame(self, parent):
        """创建地理位置输入区域"""
        location_frame = ttk.LabelFrame(parent, text="地理位置", padding="5")
        location_frame.pack(fill=tk.X, pady=(0, 10))

        # 地址输入框
        ttk.Label(location_frame, text="地址:").pack(side=tk.LEFT, padx=5)
        self.address_entry = ttk.Entry(location_frame, width=50)
        self.address_entry.pack(side=tk.LEFT, padx=5)

        # 获取经纬度按钮
        self.get_location_btn = ttk.Button(
            location_frame,
            text="获取经纬度",
            command=self.get_location
        )
        self.get_location_btn.pack(side=tk.LEFT, padx=5)

        # 经纬度显示
        self.longitude_var = tk.StringVar(value="经度: -")
        self.latitude_var = tk.StringVar(value="纬度: -")
        ttk.Label(location_frame, textvariable=self.longitude_var).pack(side=tk.LEFT, padx=10)
        ttk.Label(location_frame, textvariable=self.latitude_var).pack(side=tk.LEFT, padx=10)

    def get_location(self):
        """获取地理位置信息"""
        address = self.address_entry.get().strip()
        if not address:
            messagebox.showwarning("提示", "请输入地址")
            return

        from location_utils import get_location_by_address

        # 显示加载状态
        self.get_location_btn.config(state=tk.DISABLED, text="获取中...")
        self.log_message(f"正在获取地址 '{address}' 的位置信息...")

        def do_get_location():
            result = get_location_by_address(address)

            # 使用UI队列更新界面
            if result['status']:
                self.ui_queue.put(("location", {
                    'longitude': result['longitude'],
                    'latitude': result['latitude']
                }))
                self.log_message(f"获取位置成功 - {result['formatted_address']}")
            else:
                self.ui_queue.put(("error", "获取位置失败", result['message']))

            self.ui_queue.put(("update_ui", "button_state", "get_location_btn", "normal"))
            self.ui_queue.put(("update_ui", "button_text", "get_location_btn", "获取经纬度"))

        # 在新线程中执行请求
        threading.Thread(target=do_get_location, daemon=True).start()

class LoginDialog(simpledialog.Dialog):
    def __init__(self, parent, app):
        self.app = app
        super().__init__(parent, title="登录")

    def body(self, master):
        tk.Label(master, text="账号:").grid(row=0)
        tk.Label(master, text="密码:").grid(row=1)
        self.username_entry = tk.Entry(master)
        self.password_entry = tk.Entry(master, show="*")
        self.username_entry.grid(row=0, column=1)
        self.password_entry.grid(row=1, column=1)
        return self.username_entry

    def apply(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        url = config.API_LOGIN  # 使用配置的URL
        data = {"username": username, "password": password}
        try:
            resp = requests.post(url, json=data)
            resp.raise_for_status()
            result = resp.json()
            if result.get("code") == 1:
                self.app.authorization = result["data"]
                messagebox.showinfo("登录成功", result.get("message", "登录成功"))
                self.app.logout_button.config(state=tk.NORMAL)
                self.app.login_button.config(state=tk.DISABLED)
                print(result)
            else:
                messagebox.showerror("登录失败", result.get("message", "未知错误"))
                print(result)
        except Exception as e:
            messagebox.showerror("登录失败", str(e))

#############################################

