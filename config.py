# config.py

# API配置
API_BASE_URL = "https://smart-pipeline-parent-admin.kmyszkj.com/admin"

# 登录接口
API_LOGIN = f"{API_BASE_URL}/sys/auth/pwdLogin"

# 上传芯片数据接口
API_UPLOAD_CHIP = f"{API_BASE_URL}/pipeline/chip/batchAdd"

# 获取管道参数分页列表接口
API_PIPE_PARAMS = f"{API_BASE_URL}/pipeline/category/page"

# 请求超时时间（秒）
REQUEST_TIMEOUT = 10

# 高德地图Web服务API配置
AMAP_KEY = "d5d93164e962dc758da4d1ea46776043"
AMAP_GEOCODE_URL = 'https://restapi.amap.com/v3/geocode/geo'