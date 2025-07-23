import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, StringVar
import time
import os
import threading
import queue
from uhf_reader import UHFReader


class RFIDScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("RFID扫描器")
        self.root.geometry("1100x700")  # 增加高度以适应新控件
        self.root.resizable(True, True)

        # 创建读写器客户端
        self.uhf_reader = UHFReader(self)
        self.scanning = False
        self.connected = False

        # 用于跟踪TID出现次数的字典
        self.tid_counts = {}
        self.tid_to_id = {}  # TID到编号的映射
        self.total_scans = 0
        self.next_id = 1  # 下一个可用编号

        # 盘点模式（入库/出库/录入/安装）
        self.inventory_mode = StringVar(value="入库")

        # 管道类型
        self.pipe_types = ["请稍候..."]  # 初始值
        self.selected_pipe_type = StringVar()
        self.selected_pipe_type.set("请稍候...")

        # 管道材质
        self.pipe_materials = ["请稍候..."]  # 初始值
        self.selected_pipe_material = StringVar()
        self.selected_pipe_material.set("请稍候...")

        # 管道尺寸
        self.pipe_sizes = ["请稍候..."]  # 初始值
        self.selected_pipe_size = StringVar()
        self.selected_pipe_size.set("请稍候...")

        # 安装信息
        self.longitude_var = StringVar()  # 经度
        self.latitude_var = StringVar()  # 纬度
        self.installation_address_var = StringVar()  # 安装地址

        # UI更新队列
        self.ui_queue = queue.Queue()

        # 创建UI
        self.create_widgets()

        # 启动UI更新任务
        self.root.after(100, self.process_ui_queue)

        # 尝试自动连接设备
        self.uhf_reader.auto_connect()

        # 启动管道类型、材质、尺寸获取
        self.fetch_pipe_types()
        self.fetch_pipe_materials()
        self.fetch_pipe_sizes()

    def create_widgets(self):
        """创建应用程序界面"""
        # 主布局框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 连接设置区域
        self.create_connection_frame(main_frame)

        # 顶部控制按钮区域
        self.create_control_frame(main_frame)

        # 安装信息区域（新增）
        self.create_installation_frame(main_frame)

        # 标签计数表格框架
        self.create_table_frame(main_frame)

        # 操作日志区域
        self.create_log_frame(main_frame)

        # 底部统计信息
        self.create_footer_frame(main_frame)

    def create_installation_frame(self, parent):
        """创建安装信息区域"""
        installation_frame = ttk.LabelFrame(parent, text="安装信息", padding="5")
        installation_frame.pack(fill=tk.X, pady=(0, 10))
        self.installation_frame = installation_frame

        # 经纬度输入
        ttk.Label(installation_frame, text="经度:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.longitude_entry = ttk.Entry(installation_frame, textvariable=self.longitude_var, width=15)
        self.longitude_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(installation_frame, text="纬度:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.latitude_entry = ttk.Entry(installation_frame, textvariable=self.latitude_var, width=15)
        self.latitude_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # 安装地址输入
        ttk.Label(installation_frame, text="安装地址:").grid(row=0, column=4, padx=5, pady=5, sticky="e")
        self.installation_address_entry = ttk.Entry(installation_frame, textvariable=self.installation_address_var,
                                                    width=40)
        self.installation_address_entry.grid(row=0, column=5, padx=5, pady=5, sticky="w", columnspan=3)

        # 初始状态下禁用所有输入框
        self.longitude_entry.config(state="disabled")
        self.latitude_entry.config(state="disabled")
        self.installation_address_entry.config(state="disabled")

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

        # 更新串口设置区域可见性
        self.update_connection_ui()
        self.connection_type.trace("w", lambda *args: self.update_connection_ui())

    def create_control_frame(self, parent):
        """创建控制按钮区域"""
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # 模式选择区域
        mode_frame = ttk.Frame(control_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(mode_frame, text="盘点模式:").pack(side=tk.LEFT, padx=(0, 5))
        ttk.Radiobutton(mode_frame, text="入库", variable=self.inventory_mode, value="入库").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="出库", variable=self.inventory_mode, value="出库").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="录入", variable=self.inventory_mode, value="录入").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text="安装", variable=self.inventory_mode, value="安装").pack(side=tk.LEFT, padx=5)

        # 管道信息区域
        pipe_frame = ttk.Frame(control_frame)
        pipe_frame.pack(fill=tk.X, pady=(5, 0))

        # 管道类型选择
        ttk.Label(pipe_frame, text="管道类型:").pack(side=tk.LEFT, padx=(0, 5))
        self.pipe_type_combo = ttk.Combobox(pipe_frame,
                                            textvariable=self.selected_pipe_type,
                                            values=self.pipe_types,
                                            state="readonly",
                                            width=15)
        self.pipe_type_combo.pack(side=tk.LEFT, padx=5)

        # 管道材质选择
        ttk.Label(pipe_frame, text="管道材质:").pack(side=tk.LEFT, padx=(10, 5))
        self.pipe_material_combo = ttk.Combobox(pipe_frame,
                                                textvariable=self.selected_pipe_material,
                                                values=self.pipe_materials,
                                                state="readonly",
                                                width=15)
        self.pipe_material_combo.pack(side=tk.LEFT, padx=5)

        # 管道尺寸选择
        ttk.Label(pipe_frame, text="管道尺寸:").pack(side=tk.LEFT, padx=(10, 5))
        self.pipe_size_combo = ttk.Combobox(pipe_frame,
                                            textvariable=self.selected_pipe_size,
                                            values=self.pipe_sizes,
                                            state="readonly",
                                            width=15)
        self.pipe_size_combo.pack(side=tk.LEFT, padx=5)

        # 按钮区域
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=(5, 0))

        self.start_btn = ttk.Button(btn_frame, text="开始扫描", command=self.start_scanning)
        self.start_btn.pack(side=tk.LEFT, padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="停止扫描", command=self.stop_scanning, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)

        self.clear_btn = ttk.Button(btn_frame, text="清除所有数据", command=self.clear_all)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # 上传按钮
        self.upload_btn = ttk.Button(btn_frame, text="上传", command=self.upload_to_server, state=tk.DISABLED)
        self.upload_btn.pack(side=tk.LEFT, padx=5)

        # 状态标签
        self.status_var = tk.StringVar(value="状态: 未连接")
        status_label = ttk.Label(btn_frame, textvariable=self.status_var)
        status_label.pack(side=tk.RIGHT, padx=10)

        # 绑定盘点模式变更事件
        self.inventory_mode.trace("w", self.on_inventory_mode_change)

    def create_table_frame(self, parent):
        """创建标签计数表格区域"""
        table_frame = ttk.LabelFrame(parent, text="TID", padding="5")
        table_frame.pack(fill=tk.BOTH, expand=True)

        # 创建表格来显示TID和计数
        self.tree = ttk.Treeview(table_frame, columns=("id", "tid", "formatted_tid", "count", "last_time"),
                                 show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # 配置表格列
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
                if task[0] == "log":
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
                elif task[0] == "update_pipe_materials":
                    self.pipe_materials = task[1]
                    self.pipe_material_combo['values'] = self.pipe_materials
                    if self.pipe_materials:
                        self.selected_pipe_material.set(self.pipe_materials[0])
                    self.update_pipe_type_state()
                elif task[0] == "update_pipe_sizes":
                    self.pipe_sizes = task[1]
                    self.pipe_size_combo['values'] = self.pipe_sizes
                    if self.pipe_sizes:
                        self.selected_pipe_size.set(self.pipe_sizes[0])
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
        from server_upload import fetch_pipe_types
        fetch_thread = threading.Thread(target=fetch_pipe_types, args=(self,))
        fetch_thread.daemon = True
        fetch_thread.start()

    def fetch_pipe_materials(self):
        """获取管道材质列表"""
        from server_upload import fetch_pipe_materials
        fetch_thread = threading.Thread(target=fetch_pipe_materials, args=(self,))
        fetch_thread.daemon = True
        fetch_thread.start()

    def fetch_pipe_sizes(self):
        """获取管道尺寸列表"""
        from server_upload import fetch_pipe_sizes
        fetch_thread = threading.Thread(target=fetch_pipe_sizes, args=(self,))
        fetch_thread.daemon = True
        fetch_thread.start()

    def on_inventory_mode_change(self, *args):
        """盘点模式变更处理"""
        current_mode = self.inventory_mode.get()

        # 先清空所有输入字段
        self.selected_pipe_type.set("")
        self.selected_pipe_material.set("")
        self.selected_pipe_size.set("")
        self.longitude_var.set("")
        self.latitude_var.set("")
        self.installation_address_var.set("")

        # 先禁用所有输入框
        self.longitude_entry.config(state="disabled")
        self.latitude_entry.config(state="disabled")
        self.installation_address_entry.config(state="disabled")
        self.pipe_type_combo.config(state="disabled")
        self.pipe_material_combo.config(state="disabled")
        self.pipe_size_combo.config(state="disabled")

        # 根据不同模式启用相应输入框
        if current_mode == "录入":
            self.pipe_type_combo.config(state="readonly")
            self.pipe_material_combo.config(state="readonly")
            self.pipe_size_combo.config(state="readonly")

        elif current_mode == "安装":
            self.longitude_entry.config(state="normal")
            self.latitude_entry.config(state="normal")

        elif current_mode == "出库":
            self.installation_address_entry.config(state="normal")

    def update_pipe_type_state(self):
        """更新管道信息选择框状态"""
        current_mode = self.inventory_mode.get()

        # 管道类型、材质、尺寸在录入和安装模式下可用
        if current_mode in ["录入", "安装"]:
            self.pipe_type_combo.config(state="readonly")
            self.pipe_material_combo.config(state="readonly")
            self.pipe_size_combo.config(state="readonly")
        else:
            self.pipe_type_combo.config(state="disabled")
            self.pipe_material_combo.config(state="disabled")
            self.pipe_size_combo.config(state="disabled")

    def on_closing(self):
        """关闭窗口时清理资源"""
        self.uhf_reader.on_closing()
        self.root.destroy()