import datetime
import json
import requests
import time
from influxdb import InfluxDBClient
import logging
from filelock import FileLock

logger = logging.getLogger('streamstatus')

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

def fetch_and_process_stream_data(api_url, measurement_name):
    lock = FileLock(f"/tmp/{measurement_name}.lock", timeout=58)
    try:
        start_time = time.time()
        client = get_influx_client()

        # 关键时间对齐操作
        now_time = datetime.datetime.utcnow().replace(second=0, microsecond=0)

        try:
            # 带超时的API请求
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
                timeout=(3, 22)
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
                points.append(point)

            if points:
                batch_size = 5000  # 根据测试调整最佳批次大小
                total_points = len(points)

                for i in range(0, total_points, batch_size):
                    batch = points[i:i + batch_size]
                    try:
                        client.write_points(
                            batch,
                            time_precision='s',
                            batch_size=batch_size,
                            protocol='line'  # 使用更高效的Line Protocol格式
                        )
                    except Exception as e:
                        logger.error(f"批次 {i // batch_size} 写入失败: {str(e)}")

                logger.info(f"成功写入 {total_points} 条数据，分 {total_points // batch_size} 批次")

        except requests.exceptions.Timeout:
            logger.error(f"[{measurement_name}] API请求超时")
        except Exception as e:
            logger.error(f"[{measurement_name}] 数据处理异常: {str(e)}", exc_info=True)

    except Exception as e:
        logger.error(f"[{measurement_name}] 任务执行失败: {str(e)}")


def all_stream_task():
    api_url = "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "rapid_stream_status")


def all_goose_stream_task():
    api_url = "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "goose_rapid_stream_status")
