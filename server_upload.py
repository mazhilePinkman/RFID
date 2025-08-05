# server_upload.py
import threading
import queue
import time
import config  # 导入配置


def upload_data(app, data):
    """上传数据到服务器"""
    if not app.authorization:
        app.log_message("请先登录后再上传")
        app.ui_queue.put(("messagebox", "未登录", "请先登录后再上传数据", "error"))
        return

    # 检查是否已获取位置信息
    try:
        longitude = float(app.longitude_var.get().split(": ")[1])
        latitude = float(app.latitude_var.get().split(": ")[1])
    except (ValueError, IndexError):
        app.log_message("错误: 请先获取位置信息")
        app.ui_queue.put(("messagebox", "上传失败", "请先获取位置信息", "error"))
        return

    app.ui_queue.put(("update_ui", "button_state", "upload_btn", "disabled"))
    app.ui_queue.put(("update_ui", "button_state", "upload_btn", "上传中...", None, "text"))

    try:
        url = config.API_UPLOAD_CHIP
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RFID Scanner App",
            "Authorization": app.authorization
        }

        # 获取选中的管道参数
        selected_param = app.selected_pipe_type.get()
        pipe_params = selected_param.split()
        material_name = pipe_params[0]
        diameter_size = pipe_params[1] if len(pipe_params) > 1 else "0"

        pipeline_category_id = app.pipe_params_map.get(selected_param)
        if not pipeline_category_id:
            raise Exception("无法找到选中管道参数对应的ID")

        # 准备上传数据列表
        upload_data = []
        for item in app.tree.get_children():
            values = app.tree.item(item)['values']
            if values[0] == "√":  # 检查是否选中
                tid = values[2]  # TID在第三列
                item_data = {
                    "chipId": tid,
                    "pipelineCategoryId": pipeline_category_id,
                    "materialName": material_name,
                    "diameterSize": float(diameter_size),
                    "longitude": longitude,
                    "latitude": latitude
                }
                upload_data.append(item_data)

        import requests
        resp = requests.post(url, json=upload_data, headers=headers, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        result = resp.json()

        if result.get("code") == 1:
            app.log_message("数据上传成功")
            app.ui_queue.put(("messagebox", "上传成功", "数据已成功上传", "info"))
        else:
            error_msg = f"上传失败: {result.get('message', '未知错误')}"
            app.log_message(error_msg)
            app.ui_queue.put(("messagebox", "上传失败", error_msg, "error"))

    except Exception as e:
        error_msg = f"上传数据时出错: {str(e)}"
        app.log_message(error_msg)
        app.ui_queue.put(("messagebox", "上传失败", error_msg, "error"))
    finally:
        app.ui_queue.put(("enable_upload",))


def upload_to_server(app):
    """启动上传线程"""
    # 检查是否有选中的数据
    selected_count = sum(1 for item in app.tree.get_children()
                         if app.tree.item(item)['values'][0] == "√")

    if not selected_count:
        app.log_message("错误: 没有选中要上传的数据")
        app.ui_queue.put(("messagebox", "上传失败", "请先选择要上传的数据", "error"))
        return

    # 准备数据
    data = prepare_upload_data(app)

    # 在单独线程中上传
    upload_thread = threading.Thread(target=upload_data, args=(app, data))
    upload_thread.daemon = True
    upload_thread.start()


def prepare_upload_data(app):
    """准备上传数据"""
    # 检查是否已获取位置信息
    try:
        longitude = float(app.longitude_var.get().split(": ")[1])
        latitude = float(app.latitude_var.get().split(": ")[1])
    except (ValueError, IndexError):
        return None

    selected_param = app.selected_pipe_type.get()
    pipe_params = selected_param.split()
    material_name = pipe_params[0]
    diameter_size = pipe_params[1] if len(pipe_params) > 1 else "0"
    pipeline_category_id = app.pipe_params_map.get(selected_param)

    data = []
    for item in app.tree.get_children():
        values = app.tree.item(item)['values']
        if values[0] == "√":  # 检查是否选中
            tid = values[2]  # TID在第三列
            item_data = {
                "chipId": tid,
                "pipelineCategoryId": pipeline_category_id,
                "materialName": material_name,
                "diameterSize": float(diameter_size),
                "longitude": longitude,
                "latitude": latitude
            }
            data.append(item_data)

    return data


def fetch_pipe_params(app):
    """登录后获取管道参数列表"""
    if not app.authorization:
        app.log_message("请先登录后再获取管道参数")
        app.ui_queue.put(("messagebox", "未登录", "请先登录后再获取管道参数", "error"))
        return

    try:
        url = config.API_PIPE_PARAMS
        headers = {
            "User-Agent": "RFID Scanner App",
            "Authorization": app.authorization
        }
        import requests
        resp = requests.get(url, headers=headers, timeout=config.REQUEST_TIMEOUT)
        resp.raise_for_status()
        response_data = resp.json()  # 获取完整响应
        data_list = response_data.get('data', [])  # 从data字段取出列表

        # 存储id映射关系
        app.pipe_params_map = {}
        param_list = []

        for item in data_list:
            name = item.get('materialName', '')
            size = item.get('diameterSize', '')

            # 处理可能为空的值
            name = name.strip() if name else ''
            size = str(size).strip() if size is not None else ''

            param_key = f"{name} {size}".strip()
            param_list.append(param_key)
            # 保存id映射
            app.pipe_params_map[param_key] = item.get('id')

        print(f"获取管道参数响应: {response_data}")  # 调整为打印完整响应
        app.ui_queue.put(("update_pipe_types", param_list))
        app.log_message("管道参数列表更新成功")
    except Exception as e:
        app.log_message(f"获取管道参数时出错: {str(e)}")