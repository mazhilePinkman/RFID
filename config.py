# config.py

# API配置
API_BASE_URL = "https://smart-pipeline-parent-admin.kmyszkj.com/admin"

# 登录接口
API_LOGIN = f"{API_BASE_URL}/sys/auth/pwdLogin"

# 上传芯片数据接口
API_UPLOAD_CHIP = f"{API_BASE_URL}/pipeline/chip/batchAdd"

# 获取管道参数分页列表接口
API_PIPE_PARAMS = f"{API_BASE_URL}/pipeline/chip/list?status=0"

# 请求超时时间（秒）
REQUEST_TIMEOUT = 10

# 高德地图Web服务API配置
AMAP_KEY = "d5d93164e962dc758da4d1ea46776043"
AMAP_GEOCODE_URL = 'https://restapi.amap.com/v3/geocode/geo'



# 管道类型列表
API_PIPE_TYPES = f"{API_BASE_URL}/sys/dict/type/getByType?type=PipelineTypeEnum"

# 生产单位列表
API_MANUFACTURERS = (f"{API_BASE_URL}/trace/relevantUnits/list?type=5")

# 产品信息列表
API_PRODUCTS = (f"{API_BASE_URL}/trace/productInfo/list?")

# 原材料供应商列表
API_SUPPLIERS = (f"{API_BASE_URL}/trace/relevantUnits/list?type=1")

API_CHIP_INFO = f"{API_BASE_URL}/pipeline/chip/info"  # 芯片信息查询

API_BATCH_STORAGE = f"{API_BASE_URL}/pipeline/storage/batchAdd"  # 批量入库