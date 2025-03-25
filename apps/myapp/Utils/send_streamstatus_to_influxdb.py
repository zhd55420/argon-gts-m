import datetime
import json
import logging
import time
from filelock import FileLock
from influxdb import InfluxDBClient
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('streamstatus')

# 全局配置（可移至settings.py）
INFLUX_CONFIG = {
    "host": "15.204.133.239",
    "port": 8086,
    "database": "rapid_stream",
    "username": "uploader",
    "password": "bja!d7BB",
    "timeout": 15
}


# 带重试的Session工厂（复用连接）
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


# InfluxDB客户端（单例模式）
_client = None


def get_influx_client():
    global _client
    if _client is None:
        _client = InfluxDBClient(**INFLUX_CONFIG)
    return _client


def build_data_point(e, measurement, timestamp):
    """构建标准化数据点"""
    stream_res = e['streamResponse']
    stream_status = e['streamStatus']

    return {
        "measurement": measurement,
        "tags": {
            "stream_id": str(stream_res['streamId']),
            "source": str(stream_res['source']),
            "signalType": str(stream_res['signalType'])
        },
        "time": timestamp,
        "fields": {
            "masterStatus": bool(stream_status.get('masterStreamStatus')),
            "transcodeStatus": bool(stream_status.get('transcodeStreamStatus')),
            "receiverStatus": bool(stream_status.get('channelReceiverStreamStatus')),
            "bandWidth": stream_status.get('masterStreamStatus', {}).get('bw', 0),
            "master_server_id": str(stream_res['masterServer']['serverId']),
            "forward_server_id": str(stream_res['forwardServer']['serverId'])
        }
    }


def fetch_and_process_stream_data(api_url, measurement_name):
    """核心处理逻辑"""
    lock = FileLock(f"/tmp/{measurement_name}.lock", timeout=58)
    try:
        with lock:
            start = time.time()

            # 获取标准化时间戳
            timestamp = datetime.datetime.utcnow().replace(
                second=0, microsecond=0
            ).isoformat() + "Z"

            # API请求
            session = create_retry_session()
            try:
                res = session.post(
                    api_url,
                    json={
                        "streamRequest": {"source": ""},
                        "gooseStreamRequest": {"source": ""}
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=(3, 25),  # 总超时28秒
                    verify=False
                )
                res.raise_for_status()
                data = res.json().get('data', [])
            except Exception as e:
                logger.error(f"[{measurement_name}] API请求失败: {str(e)}")
                return

            # 构建数据点
            points = [
                build_data_point(e, measurement_name, timestamp)
                for e in data
            ]

            # 批量写入
            if points:
                try:
                    client = get_influx_client()
                    client.write_points(points, batch_size=5000)
                    logger.info(
                        f"[{measurement_name}] 写入 {len(points)} 条数据 | "
                        f"耗时 {time.time() - start:.1f}s"
                    )
                except Exception as e:
                    logger.error(f"[{measurement_name}] 写入失败: {str(e)}")
                    # 记录失败数据
                    with open(f"/tmp/{measurement_name}_failed_{timestamp}.json", "w") as f:
                        json.dump(points, f)

    except Exception as e:
        logger.error(f"[{measurement_name}] 任务异常: {str(e)}")


# 定时任务入口（保持原有settings.py配置不变）
def all_stream_task():
    fetch_and_process_stream_data(
        "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1",
        "rapid_stream_status"
    )


def all_goose_stream_task():
    fetch_and_process_stream_data(
        "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1",
        "goose_rapid_stream_status"
    )