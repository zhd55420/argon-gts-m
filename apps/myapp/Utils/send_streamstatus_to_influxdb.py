import datetime
import json
import requests
import time
from influxdb import InfluxDBClient
import logging
from filelock import FileLock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('streamstatus')

# 带重试的Session工厂
def create_retry_session():
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

# 复用数据库连接（惰性初始化）
_client = None

def get_influx_client():
    global _client
    if _client is None:
        _client = InfluxDBClient(
            host='15.204.133.239',
            port=8086,
            database='rapid_stream',
            username='uploader',
            password='bja!d7BB',
            pool_size=10
        )
    return _client


def validate_point(point):
    # 强制转换tags为字符串
    point['tags'] = {k: str(v) for k, v in point['tags'].items()}

    # 清理fields中的None值
    point['fields'] = {
        k: v if v is not None else ''
        for k, v in point['fields'].items()
    }
    return point
def fetch_and_process_stream_data(api_url, measurement_name):
    lock = FileLock(f"/tmp/{measurement_name}.lock", timeout=58)
    try:
        with lock:
            start_time = time.time()
            client = get_influx_client()

            # 关键时间对齐操作
            now_time = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat() + "Z"

            try:
                # 带超时的API请求
                session = create_retry_session()
                headers = {"Content-Type": "application/json;charset=utf-8"}
                data_request = {
                    "streamRequest": {"source": ""},
                    "gooseStreamRequest": {"source": ""}
                }

                # 请求超时设为25秒（总超时=连接3秒+读取22秒）
                res = requests.post(
                    api_url,
                    data=json.dumps(data_request),
                    headers=headers,
                    timeout=(3, 230),
                    verify=False
                )
                res.raise_for_status()

                points = []
                for e in json.loads(res.text)['data']:
                    masterStreamStatus = e['streamStatus']['masterStreamStatus'] is not None
                    transcodeStreamStatus = e['streamStatus']['transcodeStreamStatus'] is not None
                    channelReceiverStreamStatus = e['streamStatus']['channelReceiverStreamStatus'] is not None
                    bandWidth = e['streamStatus']['masterStreamStatus']['bw'] if masterStreamStatus else 0

                    point = {
                        "measurement": measurement_name,
                        "tags": {
                            "stream_id": e['streamResponse']['streamId'],
                            "source": e['streamResponse']['source'],
                            "signalType": e['streamResponse']['signalType']
                        },
                        "time": now_time,
                        "fields": {
                            "stream": e['streamResponse']['streamId'],
                            "masterStatus": masterStreamStatus,
                            "master_server_id": e['streamResponse']['masterServer']['serverId'],
                            "transcodeStatus": transcodeStreamStatus,
                            "forward_server_id": e['streamResponse']['forwardServer']['serverId'],
                            "receiverStatus": channelReceiverStreamStatus,
                            "bandWidth": bandWidth
                        }
                    }
                    point = validate_point(point)  # 数据验证
                    points.append(point)

                if points:
                    batch_size = 5000
                    for i in range(0, len(points), batch_size):
                        batch = points[i:i + batch_size]
                        try:
                            client.write_points(
                                batch,
                                protocol='line',
                                precision='s'
                            )
                            logger.debug(f"批次 {i // batch_size} 写入成功")
                        except Exception as batch_e:
                            logger.error(f"批次 {i // batch_size} 失败: {str(batch_e)}")
                            # 记录失败批次到文件
                            with open(f"/tmp/{measurement_name}_failed.log", "a") as f:
                                f.write(json.dumps(batch) + "\n")

                    logger.info(f"成功写入 {len(points)} 条数据，分 {len(points) // batch_size + 1} 批次")

            except requests.exceptions.Timeout:
                logger.error(f"[{measurement_name}] API请求超时")

    except Exception as e:
        logger.error(f"[{measurement_name}] 任务执行失败: {str(e)}")


def all_stream_task():
    api_url = "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "rapid_stream_status")


def all_goose_stream_task():
    api_url = "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "goose_rapid_stream_status")
