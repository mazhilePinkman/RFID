import requests
import config


def get_location_by_address(address):
    """通过地址获取经纬度"""
    try:
        params = {
            'key': config.AMAP_KEY,
            'address': address,
            'output': 'json'
        }

        response = requests.get(config.AMAP_GEOCODE_URL, params=params)
        response.raise_for_status()
        result = response.json()

        if result.get('status') == '1':  # 请求成功
            if result.get('geocodes') and len(result['geocodes']) > 0:
                location = result['geocodes'][0]['location']  # 格式: "经度,纬度"
                lng, lat = location.split(',')
                return {
                    'status': True,
                    'longitude': lng,
                    'latitude': lat,
                    'formatted_address': result['geocodes'][0].get('formatted_address', '')
                }
            else:
                return {
                    'status': False,
                    'message': '未找到该地址对应的位置信息'
                }
        else:
            return {
                'status': False,
                'message': result.get('info', '请求失败')
            }
        print(f"Request URL: {config.AMAP_GEOCODE_URL}")
        print(f"Params: {params}")
        print(f"Response: {result}")
    except Exception as e:
        return {
            'status': False,
            'message': f'获取位置信息时出错: {str(e)}'
        }