import json
import base64
import urllib.request
import ssl
import threading
import queue
import time


def upload_data(app, data):
    """上传数据到服务器的函数"""
    # 禁用上传按钮防止多次点击
    app.ui_queue.put(("update_ui", "button_state", "upload_btn", "disabled"))
    app.ui_queue.put(("update_ui", "button_state", "upload_btn", "上传中...", None, "text"))

    try:
        # 根据模式确定API端点
        mode = app.inventory_mode.get()
        if mode == "录入":
            api_endpoint = "/api/register"
        else:
            api_endpoint = "/api/inventory"

        # 服务器配置
        server_ip = "192.168.0.1"
        server_port = 8080
        url = f"http://{server_ip}:{server_port}{api_endpoint}"

        # 准备请求数据
        json_data = json.dumps(data).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "RFID Scanner App"
        }

        context = ssl._create_unverified_context()
        request = urllib.request.Request(url, data=json_data, headers=headers)

        try:
            with urllib.request.urlopen(request, context=context, timeout=30) as response:
                response_data = response.read().decode("utf-8")
                response_json = json.loads(response_data)

                if response.getcode() == 200:
                    app.log_message(f"数据上传成功: {response_json.get('message', '')}")
                    success_msg = f"数据已成功上传到服务器！\n服务器响应: {response_json.get('message', '')}"
                    app.ui_queue.put(("messagebox", "上传成功", success_msg, "info"))
                else:
                    error_msg = f"上传失败: {response.getcode()} - {response_json.get('error', '未知错误')}"
                    app.log_message(error_msg)
                    app.ui_queue.put(("messagebox", "上传失败", error_msg, "error"))
        except urllib.error.URLError as e:
            error_msg = f"无法连接到服务器: {str(e.reason)}"
            app.log_message(error_msg)
            app.ui_queue.put(("messagebox", "连接错误", error_msg, "error"))
        except Exception as e:
            error_msg = f"上传过程中发生错误: {str(e)}"
            app.log_message(error_msg)
            app.ui_queue.put(("messagebox", "上传失败", error_msg, "error"))

    except Exception as e:
        error_msg = f"上传到服务器时出错: {str(e)}"
        app.log_message(error_msg)
        app.ui_queue.put(("messagebox", "上传失败", error_msg, "error"))
    finally:
        # 恢复上传按钮
        app.ui_queue.put(("enable_upload",))


def prepare_upload_data(app):
    """准备上传数据"""
    mode = app.inventory_mode.get()
    data = {
        "operation": mode,
        "tids": []  # 修改为只包含TID的列表
    }

    # 只添加TID，不包含时间戳
    for tid in app.tid_counts.keys():
        # 录入模式下添加管道类型
        if mode == "录入":
            # 创建一个包含TID和管道类型的对象
            item = {
                "tid": tid,
                "pipe_type": app.selected_pipe_type.get()
            }
            data["tids"].append(item)
        else:
            # 其他模式只添加TID字符串
            data["tids"].append(tid)

    return data


def fetch_pipe_types(app):
    """从服务器获取管道类型列表"""
    try:
        server_ip = "192.168.0.1"
        server_port = 8080
        url = f"http://{server_ip}:{server_port}/api/pipeTypes"

        context = ssl._create_unverified_context()
        request = urllib.request.Request(url)
        request.add_header("User-Agent", "RFID Scanner App")

        with urllib.request.urlopen(request, context=context, timeout=10) as response:
            if response.getcode() == 200:
                response_data = response.read().decode("utf-8")
                pipe_types = json.loads(response_data).get("pipe_types", [])
                app.ui_queue.put(("update_pipe_types", pipe_types))
                app.log_message("管道类型列表更新成功")
            else:
                app.log_message(f"获取管道类型失败: HTTP {response.getcode()}")
    except Exception as e:
        app.log_message(f"获取管道类型时出错: {str(e)}")


def upload_to_server(app):
    """上传数据到服务器"""
    if not app.tid_counts:
        app.log_message("错误: 没有可上传的数据")
        app.ui_queue.put(("messagebox", "上传失败", "没有可上传的数据", "error"))
        return

    # 准备数据
    data = prepare_upload_data(app)

    # 在单独线程中上传
    upload_thread = threading.Thread(target=upload_data, args=(app, data))
    upload_thread.daemon = True
    upload_thread.start()
