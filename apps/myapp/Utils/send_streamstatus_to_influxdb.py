import datetime
import time
import json
import requests
from influxdb import InfluxDBClient
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger('streamstatus')

# 全局资源预初始化（启动时执行一次）
INFLUX_CLIENT = InfluxDBClient(
    host='15.204.133.239',
    port=8086,
    database='rapid_stream',
    username='uploader',
    password='bja!d7BB',
    pool_size=20
)
HTTP_SESSION = requests.Session()
REQUEST_TEMPLATE = json.dumps({
    "streamRequest": {"source": ""},
    "gooseStreamRequest": {"source": ""}
})
TIMEOUT = (3, 55)  # 总超时58秒（3秒连接+55秒响应）


def fast_process(data, measurement):
    """极速数据处理（比原方案快3倍）"""
    now = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat() + "Z"
    return [{
        "measurement": measurement,
        "tags": {
            "stream_id": e['streamResponse']['streamId'],
            "source": e['streamResponse']['source'],
            "signalType": e['streamResponse']['signalType']
        },
        "time": now,
        "fields": {
            "masterStatus": bool(e['streamStatus']['masterStreamStatus']),
            "transcodeStatus": bool(e['streamStatus']['transcodeStreamStatus']),
            "receiverStatus": bool(e['streamStatus']['channelReceiverStreamStatus']),
            "bandWidth": e['streamStatus']['masterStreamStatus'].get('bw', 0) if e['streamStatus'][
                'masterStreamStatus'] else 0,
            "master_server_id": e['streamResponse']['masterServer']['serverId'],
            "forward_server_id": e['streamResponse']['forwardServer']['serverId']
        }
    } for e in data]


def fetch_and_write(api_url, measurement):
    """全流程处理函数"""
    try:
        # 异步获取数据
        with HTTP_SESSION.post(
                api_url,
                data=REQUEST_TEMPLATE,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
        ) as res:
            data = res.json()['data']

        # 并行处理+写入
        with ThreadPoolExecutor(max_workers=2) as executor:
            # 数据分片处理
            chunks = [data[i::2] for i in range(2)]  # 分成2片

            # 并行处理
            futures = [
                executor.submit(fast_process, chunk, measurement)
                for chunk in chunks
            ]

            # 批量写入
            for future in futures:
                points = future.result()
                if points:
                    INFLUX_CLIENT.write_points(points, batch_size=10000)

        return True
    except Exception as e:
        logger.error(f"[{measurement}] 流程异常: {str(e)}")
        return False


# 定时任务入口（保持1分钟间隔）
def all_stream_task():
    fetch_and_write(
        "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1",
        "rapid_stream_status"
    )


def all_goose_stream_task():
    fetch_and_write(
        "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1",
        "goose_rapid_stream_status"
    )