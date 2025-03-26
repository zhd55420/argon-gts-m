import datetime
import time
import json
import requests
from influxdb import InfluxDBClient
import logging
from filelock import FileLock

logger = logging.getLogger('streamstatus')

# 全局单例客户端（保持长连接）
INFLUX_CLIENT = InfluxDBClient(
    host='15.204.133.239',
    port=8086,
    database='rapid_stream',
    username='uploader',
    password='bja!d7BB',
    pool_size=10  # 启用连接池
)

# 预定义请求模板（避免重复生成）
REQUEST_TEMPLATE = json.dumps({
    "streamRequest": {"source": ""},
    "gooseStreamRequest": {"source": ""}
})


def fetch_and_process_stream_data(api_url, measurement_name):
    lock = FileLock(f"/tmp/{measurement_name}.lock", timeout=58)
    try:
        with lock:
            start_time = time.time()
            timestamp = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat() + "Z"

            # 复用Session提升网络性能
            with requests.Session() as session:
                res = session.post(
                    api_url,
                    data=REQUEST_TEMPLATE,
                    headers={"Content-Type": "application/json"},
                )
                res.raise_for_status()

                # 流式解析提升大响应处理速度
                data = res.json()['data']
                points = [{
                    "measurement": measurement_name,
                    "tags": {
                        "stream_id": str(e['streamResponse']['streamId']),
                        "source": str(e['streamResponse']['source']),
                        "signalType": str(e['streamResponse']['signalType'])
                    },
                    "time": timestamp,
                    "fields": {
                        "masterStatus": bool(e['streamStatus']['masterStreamStatus']),
                        "transcodeStatus": bool(e['streamStatus']['transcodeStreamStatus']),
                        "receiverStatus": bool(e['streamStatus']['channelReceiverStreamStatus']),
                        "bandWidth": e['streamStatus']['masterStreamStatus'].get('bw', 0) if e['streamStatus'][
                            'masterStreamStatus'] else 0,
                        "master_server_id": str(e['streamResponse']['masterServer']['serverId']),
                        "forward_server_id": str(e['streamResponse']['forwardServer']['serverId'])
                    }
                } for e in data]

            # 批量写入优化
            if points:
                try:
                    INFLUX_CLIENT.write_points(
                        points,
                        batch_size=5000,
                        time_precision='s'
                    )
                    logger.info(
                        f"[{measurement_name}] 写入成功 | 数量:{len(points)} | 耗时:{time.time() - start_time:.1f}s")
                except Exception as e:
                    logger.error(f"[{measurement_name}] 写入失败: {str(e)}")

    except Exception as e:
        logger.error(f"[{measurement_name}] 任务异常: {str(e)}")


# 任务入口保持简洁
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