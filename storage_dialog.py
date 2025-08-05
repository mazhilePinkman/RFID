import tkinter as tk
from tkinter import ttk, messagebox
import requests
import config


class StorageDialog(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("入库管理")
        self.geometry("900x600")

        # 添加扫描状态变量
        self.scanning = False

        # 初始化数据字典
        self.pipe_types_map = {}
        self.manufacturers_map = {}
        self.products_map = {}
        self.suppliers_map = {}

        # 绑定窗口关闭事件
        self.protocol("WM_DELETE_WINDOW", self.on_closing)  # 添加这一行

        self.create_widgets()
        self.fetch_all_data()

    def create_widgets(self):
        # 创建下拉框区域
        control_frame = ttk.LabelFrame(self, text="入库信息", padding=10)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # 管道类型
        ttk.Label(control_frame, text="管道类型*:").grid(row=0, column=0, padx=5, pady=5)
        self.pipe_type_var = tk.StringVar()
        self.pipe_type_combo = ttk.Combobox(control_frame, textvariable=self.pipe_type_var, state="readonly", width=20)
        self.pipe_type_combo.grid(row=0, column=1, padx=5, pady=5)

        # 生产单位
        ttk.Label(control_frame, text="生产单位*:").grid(row=0, column=2, padx=5, pady=5)
        self.manufacturer_var = tk.StringVar()
        self.manufacturer_combo = ttk.Combobox(control_frame, textvariable=self.manufacturer_var, state="readonly",
                                               width=20)
        self.manufacturer_combo.grid(row=0, column=3, padx=5, pady=5)

        # 产品信息
        ttk.Label(control_frame, text="产品信息*:").grid(row=1, column=0, padx=5, pady=5)
        self.product_var = tk.StringVar()
        self.product_combo = ttk.Combobox(control_frame, textvariable=self.product_var, state="readonly", width=20)
        self.product_combo.grid(row=1, column=1, padx=5, pady=5)

        # 原材料供应商
        ttk.Label(control_frame, text="原材料供应商:").grid(row=1, column=2, padx=5, pady=5)
        self.supplier_var = tk.StringVar()
        self.supplier_combo = ttk.Combobox(control_frame, textvariable=self.supplier_var, state="readonly", width=20)
        self.supplier_combo.grid(row=1, column=3, padx=5, pady=5)

        # 按钮区域
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)

        ##new
        self.scan_button = ttk.Button(button_frame, text="开始扫描", command=self.toggle_scan)
        self.scan_button.pack(side=tk.LEFT, padx=5)

        ttk.Button(button_frame, text="查询信息", command=self.query_chip_info).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="批量入库", command=self.batch_storage).pack(side=tk.LEFT, padx=5)

        # 创建表格
        self.create_table()

    def create_table(self):
        table_frame = ttk.Frame(self)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 创建表格
        columns = ("select", "id", "tid", "material", "diameter")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        # 配置列
        self.tree.heading("select", text="选择")
        self.tree.heading("id", text="编号")
        self.tree.heading("tid", text="TID")
        self.tree.heading("material", text="管道材质")
        self.tree.heading("diameter", text="管径")

        # 设置列宽
        self.tree.column("select", width=10)
        self.tree.column("id", width=50)
        self.tree.column("tid", width=200)
        self.tree.column("material", width=100)
        self.tree.column("diameter", width=100)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 从主窗口复制数据
        self.copy_data_from_main()

        # 绑定点击事件
        self.tree.bind('<Button-1>', self.on_tree_click)

    def fetch_all_data(self):
        """获取所有下拉框数据"""
        self.fetch_pipe_types()
        self.fetch_manufacturers()
        self.fetch_products()
        self.fetch_suppliers()

    def fetch_data(self, url, combo, data_map):
        """通用数据获取方法"""
        try:
            headers = {"Authorization": self.app.authorization}
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

            if data.get("code") == 1:
                items = data.get("data", [])
                names = []
                for item in items:
                    name = item.get("name", "")
                    data_map[name] = item.get("id")
                    names.append(name)
                combo["values"] = names
                if names:
                    combo.set(names[0])
            else:
                messagebox.showerror("错误", f"获取数据失败: {data.get('message', '未知错误')}")
        except Exception as e:
            messagebox.showerror("错误", f"获取数据失败: {str(e)}")

    def fetch_data_t(self, url, combo, data_map):
        try:
            headers = {"Authorization": self.app.authorization}

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()

            if data.get("code") != 1:
                error_msg = data.get("message", "未知错误")
                raise ValueError(f"API响应错误: {error_msg}")

            items = data.get("data", {}).get("dataList", [])  # 多级安全访问[7](@ref)
            names = []

            for item in items:
                label = item.get("dictLabel", "")
                value = item.get("dictValue")

                # 8. 验证必要字段
                if not label or value is None:  # 跳过无效数据[7](@ref)
                    continue

                data_map[label] = value
                names.append(label)

            # 9. 更新UI组件
            combo["values"] = names
            if names:
                combo.set(names[0])

        # 10. 更具体的异常处理
        except requests.exceptions.RequestException as e:  # 网络相关异常[6](@ref)
            messagebox.showerror("网络错误", f"请求失败: {str(e)}")
        except ValueError as e:  # 业务逻辑错误[7](@ref)
            messagebox.showerror("数据错误", str(e))
        except Exception as e:  # 兜底异常处理[6,7](@ref)
            messagebox.showerror("系统错误", f"未处理的异常: {str(e)}")

    def fetch_pipe_types(self):
        self.fetch_data_t(config.API_PIPE_TYPES, self.pipe_type_combo, self.pipe_types_map)

    def fetch_manufacturers(self):
        self.fetch_data(config.API_MANUFACTURERS, self.manufacturer_combo, self.manufacturers_map)

    def fetch_products(self):
        self.fetch_data(config.API_PRODUCTS, self.product_combo, self.products_map)

    def fetch_suppliers(self):
        self.fetch_data(config.API_SUPPLIERS, self.supplier_combo, self.suppliers_map)

    def copy_data_from_main(self):
        """从主窗口复制数据到表格"""
        for item in self.app.tree.get_children():
            values = self.app.tree.item(item)["values"]
            self.tree.insert("", "end", values=("", values[1], values[2], "", ""))

    def on_tree_click(self, event):
        """处理表格点击事件"""
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            if column == "#1":  # 选择列
                item = self.tree.identify_row(event.y)
                if item:
                    current_state = self.tree.item(item)["values"][0]
                    new_state = "√" if current_state != "√" else ""
                    values = list(self.tree.item(item)["values"])
                    values[0] = new_state
                    self.tree.item(item, values=values)

    def query_chip_info(self):
        """查询芯片信息"""
        try:
            headers = {"Authorization": self.app.authorization}
            for item in self.tree.get_children():
                values = list(self.tree.item(item)["values"])
                tid = values[2]

                response = requests.get(
                    f"{config.API_CHIP_INFO}?chipId={tid}",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") == 1:
                    chip_info = data.get("data", {})
                    values[3] = chip_info.get("materialName", "")
                    values[4] = str(chip_info.get("diameterSize", ""))
                    self.tree.item(item, values=values)
        except Exception as e:
            messagebox.showerror("错误", f"查询信息失败: {str(e)}")

    def toggle_scan(self):
        """切换扫描状态"""
        if not self.scanning:
            self.scanning = True
            self.scan_button.configure(text="停止扫描")
            self.app.uhf_reader.callEpcInfo = self.received_epc  # 重定向回调函数
            self.app.uhf_reader.start_scanning()
        else:
            self.scanning = False
            self.scan_button.configure(text="开始扫描")
            self.app.uhf_reader.stop_scanning()
            self.app.uhf_reader.callEpcInfo = self.app.received_epc  # 恢复原回调函数

    def batch_storage(self):
        """批量入库"""
        # 检查必填项
        if not all([self.pipe_type_var.get(), self.manufacturer_var.get(), self.product_var.get()]):
            messagebox.showerror("错误", "请填写所有必填项（标记*的字段）")
            return

        # 检查是否有选中的芯片
        selected_items = [item for item in self.tree.get_children()
                          if self.tree.item(item)["values"][0] == "√"]
        if not selected_items:
            messagebox.showerror("错误", "请选择要入库的芯片")
            return

        try:
            # 准备请求数据
            data = []
            for item in selected_items:
                values = self.tree.item(item)["values"]
                data.append({
                    "chipId": values[2],
                    "pipelineTypeId": self.pipe_types_map[self.pipe_type_var.get()],
                    "manufacturerId": self.manufacturers_map[self.manufacturer_var.get()],
                    "productId": self.products_map[self.product_var.get()],
                    "supplierId": self.suppliers_map.get(self.supplier_var.get()),
                    "materialName": values[3],
                    "diameterSize": float(values[4]) if values[4] else 0
                })

            # 发送请求
            headers = {
                "Authorization": self.app.authorization,
                "Content-Type": "application/json"
            }
            response = requests.post(
                config.API_BATCH_STORAGE,
                json=data,
                headers=headers
            )
            response.raise_for_status()
            result = response.json()

            if result.get("code") == 1:
                messagebox.showinfo("成功", "批量入库成功")
                self.destroy()  # 关闭窗口
            else:
                messagebox.showerror("错误", f"入库失败: {result.get('message', '未知错误')}")
        except Exception as e:
            messagebox.showerror("错误", f"入库失败: {str(e)}")


    def received_epc(self, epcInfo):
        """处理接收到的EPC标签信息"""
        if epcInfo.result == 0 and epcInfo.tid:
            tid_str = epcInfo.tid

            # 检查是否已存在该TID
            existing_items = {}
            for item in self.tree.get_children():
                values = self.tree.item(item)["values"]
                existing_items[values[2]] = item

            if tid_str in existing_items:
                # 更新已存在项的值
                values = list(self.tree.item(existing_items[tid_str])["values"])
                self.tree.item(existing_items[tid_str], values=values)
            else:
                # 添加新项
                next_id = len(self.tree.get_children()) + 1
                self.tree.insert("", "end", values=("", next_id, tid_str, "", ""))

    def on_closing(self):
        """关闭窗口时的处理"""
        if self.scanning:
            self.app.uhf_reader.stop_scanning()
            self.app.uhf_reader.callEpcInfo = self.app.received_epc
        self.destroy()