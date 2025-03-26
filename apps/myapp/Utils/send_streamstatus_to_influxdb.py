import datetime
import time
import json
import requests
from influxdb import InfluxDBClient
import logging
from filelock import FileLock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger('streamstatus')

# 配置常量（可提取到settings.py）
INFLUX_CONFIG = {
    "host": "15.204.133.239",
    "port": 8086,
    "database": "rapid_stream",
    "username": "uploader",
    "password": "bja!d7BB",
    "timeout": 30,
    "retries": Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(['POST'])
    )
}

# 全局客户端（保持长连接）
INFLUX_CLIENT = InfluxDBClient(**INFLUX_CONFIG)


def create_http_session():
    """创建带重试机制的HTTP会话"""
    session = requests.Session()
    adapter = HTTPAdapter(
        max_retries=INFLUX_CONFIG['retries'],
        pool_connections=20,
        pool_maxsize=100
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def fetch_and_process_stream_data(api_url, measurement_name):
    lock = FileLock(f"/tmp/{measurement_name}.lock", timeout=120)
    try:
        with lock:
            start_time = time.time()
            timestamp = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat() + "Z"

            # 使用带重试的会话
            with create_http_session() as session:
                try:
                    # 分块流式请求（避免内存峰值）
                    with session.post(
                            api_url,
                            json={"streamRequest": {"source": ""}, "gooseStreamRequest": {"source": ""}},
                            headers={"Content-Type": "application/json"},
                            timeout=(5, 45),  # 连接5s，读取45s
                            stream=True  # 启用流式传输
                    ) as res:
                        res.raise_for_status()

                        # 流式处理响应
                        points = []
                        for chunk in res.iter_content(chunk_size=1024 * 1024):  # 1MB/chunk
                            if chunk:
                                data = json.loads(chunk.decode('utf-8'))['data']
                                points.extend(process_data(data, measurement_name, timestamp))

                                # 分段写入（每1万条写入一次）
                                if len(points) >= 10000:
                                    write_to_influx(points[:10000], measurement_name)
                                    points = points[10000:]

                        # 写入剩余数据
                        if points:
                            write_to_influx(points, measurement_name)

                        logger.info(f"[{measurement_name}] 处理完成 | 总耗时:{time.time() - start_time:.1f}s")

                except requests.exceptions.Timeout:
                    logger.warning(f"[{measurement_name}] 请求超时，已重试{INFLUX_CONFIG['retries'].total}次")
                except Exception as e:
                    logger.error(f"[{measurement_name}] 请求异常: {str(e)}")

    except Exception as e:
        logger.error(f"[{measurement_name}] 任务异常: {str(e)}")


def process_data(data, measurement, timestamp):
    """高效处理数据"""
    return [{
        "measurement": measurement,
        "tags": {
            "stream_id": str(item['streamResponse']['streamId']),
            "source": str(item['streamResponse']['source']),
            "signalType": str(item['streamResponse']['signalType'])
        },
        "time": timestamp,
        "fields": {
            "masterStatus": bool(item['streamStatus']['masterStreamStatus']),
            "transcodeStatus": bool(item['streamStatus']['transcodeStreamStatus']),
            "receiverStatus": bool(item['streamStatus']['channelReceiverStreamStatus']),
            "bandWidth": item['streamStatus']['masterStreamStatus'].get('bw', 0) if item['streamStatus'][
                'masterStreamStatus'] else 0,
            "master_server_id": str(item['streamResponse']['masterServer']['serverId']),
            "forward_server_id": str(item['streamResponse']['forwardServer']['serverId'])
        }
    } for item in data]


def write_to_influx(points, measurement):
    """带重试的写入操作"""
    try:
        INFLUX_CLIENT.write_points(points, batch_size=10000)
    except Exception as e:
        logger.error(f"[{measurement}] 写入失败: {str(e)}")
        # 将失败数据存入临时队列
        with open(f"/tmp/{measurement}_retry_queue.json", "a") as f:
            json.dump(points, f)
            f.write("\n")


# 任务入口保持不变
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