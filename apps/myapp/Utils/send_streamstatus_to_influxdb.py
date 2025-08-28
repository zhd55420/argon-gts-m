import datetime
import time
import json
import requests
import gzip  # 新增：用于解压Gzip响应
from io import BytesIO  # 新增：内存缓冲区
from influxdb import InfluxDBClient
import ijson
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


def process_stream_element(measurementname,element, timestamp):
    """处理单条流数据，将所有明确为null或空的值统一转为字符串"Null" """
    try:
        if element is None:
            logger.warning("单条流数据为空，跳过处理")
            return None

        NULL_PLACEHOLDER = "Null"  # 统一空值占位符

        # -------------------------- 1. 处理streamResponse（基础标识） --------------------------
        # 即使streamResponse为null，也转为空字典处理
        stream_response = element.get('streamResponse') or {}  # 关键：处理streamResponse为null的情况

        # streamId（核心标识，若为null或空→"Null"）
        stream_id = stream_response.get('streamId')
        stream_id = str(stream_id) if stream_id is not None and stream_id != "" else NULL_PLACEHOLDER

        # source（流来源，如"INTERNET"，空值→"Null"）
        source = stream_response.get('source')
        source = str(source) if source is not None and source != "" else NULL_PLACEHOLDER

        # masterServer（主服务器信息，若为null→空字典）
        master_server = stream_response.get('masterServer') or {}
        master_server_id = master_server.get('serverId')
        master_server_id = str(
            master_server_id) if master_server_id is not None and master_server_id != "" else NULL_PLACEHOLDER

        # forwardServer（转发服务器信息，若为null→空字典）
        forward_server = stream_response.get('forwardServer') or {}
        forward_server_id = forward_server.get('serverId')
        forward_server_id = str(
            forward_server_id) if forward_server_id is not None and forward_server_id != "" else NULL_PLACEHOLDER

        # -------------------------- 2. 处理streamStatus（流状态，可能全为null） --------------------------
        stream_status = element.get('streamStatus') or {}  # 处理streamStatus为null的情况

        # masterStreamStatus（主流状态，示例中为null→特殊处理）
        master_stream = stream_status.get('masterStreamStatus')  # 可能是null
        # 若为null，直接标记为"Null"相关状态
        if master_stream is None:
            master_stream = {"is_null": True}  # 用标记区分"null"和"空字典"
        else:
            master_stream["is_null"] = False  # 正常数据标记

        # transcodeStreamStatus（转码流状态，示例中为null→同理处理）
        transcode_stream = stream_status.get('transcodeStreamStatus') or {"is_null": True}
        if transcode_stream is not None and "is_null" not in transcode_stream:
            transcode_stream["is_null"] = False

        # -------------------------- 3. 提取视频/音频编码（可能因master_stream为null而空） --------------------------
        # 视频编码（若master_stream为null→"Null"）
        video_codec = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            video_streams = master_stream.get('videoStreams', [{}])
            first_video = video_streams[0] if video_streams else {}
            video_codec_val = first_video.get('codec')
            video_codec = str(
                video_codec_val) if video_codec_val is not None and video_codec_val != "" else NULL_PLACEHOLDER

        # 音频编码（同理）
        audio_codec = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            audio_streams = master_stream.get('audioStreams', [{}])
            first_audio = audio_streams[0] if audio_streams else {}
            audio_codec_val = first_audio.get('codec')
            audio_codec = str(
                audio_codec_val) if audio_codec_val is not None and audio_codec_val != "" else NULL_PLACEHOLDER

        # 主流状态码（若master_stream为null→"Null"）
        master_status_code = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            code_val = master_stream.get('code')
            master_status_code = str(code_val) if code_val is not None else NULL_PLACEHOLDER

        # -------------------------- 4. 提取字段（Field）：处理null和空值 --------------------------
        # 主流状态（是否存在，若master_stream为null→"Null"）
        master_status = NULL_PLACEHOLDER if master_stream.get("is_null") else bool(master_stream)

        # 转码流状态（同理）
        transcode_status = NULL_PLACEHOLDER if transcode_stream.get("is_null") else bool(transcode_stream)

        # 带宽（若master_stream为null→"Null"）
        master_bandwidth = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            bw_val = master_stream.get('bw')
            master_bandwidth = bw_val if bw_val is not None else NULL_PLACEHOLDER

        # 转码带宽（同理）
        transcode_bandwidth = NULL_PLACEHOLDER
        if not transcode_stream.get("is_null"):
            tc_bw_val = transcode_stream.get('bw')
            transcode_bandwidth = tc_bw_val if tc_bw_val is not None else NULL_PLACEHOLDER

        # 延迟（avg_rtt，若master_stream为null→"Null"）
        avg_rtt = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            brt_client = master_stream.get('parameters', {}).get('brt_client', {})
            rtt_val = brt_client.get('avg_packet_rtt')
            if rtt_val is not None:
                avg_rtt = round(rtt_val / 1000, 2)  # 微秒转毫秒
            else:
                avg_rtt = NULL_PLACEHOLDER

        # 丢包数（同理）
        drop_block_count = NULL_PLACEHOLDER
        recv_block_count = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            brt_client = master_stream.get('parameters', {}).get('brt_client', {})
            brtmicro_client = brt_client.get('brtmicro_client', {})
            drop_val = brtmicro_client.get('drop_block_cnt')
            recv_val = brtmicro_client.get('recv_block_cnt')
            drop_block_count = drop_val if drop_val is not None else NULL_PLACEHOLDER
            recv_block_count = recv_val if recv_val is not None else NULL_PLACEHOLDER

        # 音视频参数（若master_stream为null→"Null"）
        video_width = video_height = video_bitrate = NULL_PLACEHOLDER
        audio_channel = audio_sample_rate = NULL_PLACEHOLDER
        if not master_stream.get("is_null"):
            video_streams = master_stream.get('videoStreams', [{}])
            first_video = video_streams[0] if video_streams else {}
            video_width = first_video.get('width') if first_video.get('width') is not None else NULL_PLACEHOLDER
            video_height = first_video.get('height') if first_video.get('height') is not None else NULL_PLACEHOLDER
            video_bitrate = first_video.get('bitRate') if first_video.get('bitRate') is not None else NULL_PLACEHOLDER

            audio_streams = master_stream.get('audioStreams', [{}])
            first_audio = audio_streams[0] if audio_streams else {}
            audio_channel = first_audio.get('channel') if first_audio.get('channel') is not None else NULL_PLACEHOLDER
            audio_sample_rate = first_audio.get('sample_rate') if first_audio.get(
                'sample_rate') is not None else NULL_PLACEHOLDER

        # 转发服务器心跳时间（若transcode_stream为null→"Null"）
        forward_heartbeat_time = NULL_PLACEHOLDER
        if not transcode_stream.get("is_null"):
            forward_params = transcode_stream.get('parameters', {})
            heartbeat_val = forward_params.get('last_heartbeat_us_time')
            if heartbeat_val is not None and heartbeat_val != "":
                forward_heartbeat_time = f"{str(heartbeat_val).replace(' ', 'T')}Z"
            else:
                forward_heartbeat_time = NULL_PLACEHOLDER

        return {
            "measurement": measurementname,
            "tags": {
                "stream_id": stream_id,
                "source": source,
                "master_server_id": master_server_id,
                "forward_server_id": forward_server_id,
                "video_codec": video_codec,
                "audio_codec": audio_codec,
                "master_status_code": master_status_code
            },
            "time": timestamp,
            "fields": {
                "master_status": master_status,
                "transcode_status": transcode_status,
                "master_bandwidth": master_bandwidth,
                "transcode_bandwidth": transcode_bandwidth,
                "avg_rtt": avg_rtt,
                "drop_block_count": drop_block_count,
                "recv_block_count": recv_block_count,
                "video_width": video_width,
                "video_height": video_height,
                "video_bitrate": video_bitrate,
                "audio_channel": audio_channel,
                "audio_sample_rate": audio_sample_rate,
                "forward_heartbeat_time": forward_heartbeat_time
            }
        }
    except Exception as e:
        logger.warning(
            f"处理单条流数据失败: {str(e)} | "
            f"问题数据: {json.dumps(element, ensure_ascii=False, default=str)[:500]}",
            exc_info=True
        )
        return None


def fetch_and_process_stream_data(api_url, measurement_name):
    """完整流程：处理Gzip压缩响应+流式解析+分批写入"""
    start_total = time.time()
    lock_path = f"/tmp/{measurement_name}.lock"
    dt = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    # 将 datetime 转成纳秒整数（1秒=10^9纳秒）
    timestamp = int(dt.timestamp() * 10 ** 9)
    total_processed = 0
    total_written = 0
    batch_size = 1000
    points_buffer = []

    try:
        # 1. 发起API请求（启用流式响应）
        start_network = time.time()
        with requests.Session() as session:
            try:
                res = session.post(
                    api_url,
                    data=REQUEST_TEMPLATE,
                    headers={"Content-Type": "application/json"},
                    stream=True,

                )
                res.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"API请求失败: {str(e)}")
                return

        network_time = time.time() - start_network
        logger.info(f"API请求完成 | 耗时: {network_time:.2f}s | 状态码: {res.status_code}")

        # 2. 处理Gzip压缩（核心修复点）
        # 检查响应是否为Gzip压缩
        content_encoding = res.headers.get('Content-Encoding', '')
        if content_encoding == 'gzip':
            logger.info("响应为Gzip压缩格式，开始解压...")
            # 创建Gzip解压流
            gzip_stream = gzip.GzipFile(fileobj=res.raw, mode='rb')
            # 将解压后的数据转换为可被ijson解析的文件对象
            raw_stream = BytesIO(gzip_stream.read())
        else:
            # 非压缩响应直接使用原始流
            raw_stream = res.raw

        # 3. 流式解析JSON
        start_parse = time.time()
        # 注意：确保此处的解析路径与API响应结构一致（如"data.item"）
        parser = ijson.items(raw_stream, 'data.item')
        for element in parser:
            total_processed += 1
            point = process_stream_element(measurement_name,element, timestamp)
            if point:
                points_buffer.append(point)

            if len(points_buffer) >= batch_size:
                written = write_points_batch(points_buffer, lock_path)
                total_written += written
                points_buffer = []

            if total_processed % 10000 == 0:
                logger.info(f"进度 | 已处理: {total_processed}条 | 已写入: {total_written}条")

        # 处理剩余数据
        if points_buffer:
            written = write_points_batch(points_buffer, lock_path)
            total_written += written

        parse_time = time.time() - start_parse
        logger.info(f"数据解析完成 | 总处理: {total_processed}条 | 解析耗时: {parse_time:.2f}s")

    except Exception as e:
        logger.error(f"整体流程异常: {str(e)}", exc_info=True)
    finally:
        total_time = time.time() - start_total
        logger.info(
            f"任务结束 | 总耗时: {total_time:.2f}s | "
            f"处理总数: {total_processed}条 | "
            f"写入成功: {total_written}条"
        )


def write_points_batch(points, lock_path):
    """
    批量写入InfluxDB（独立函数）
    优化点：1. Line Protocol格式（比write_points高效）；2. 仅写入时加锁（减少锁等待）
    """
    if not points:
        return 0
    batch_size = len(points)
    start_write = time.time()

    try:
        # 仅在写入时加锁（避免锁持有时间过长），超时10秒（防止死锁）
        with FileLock(lock_path, timeout=10):
            # 拼接Line Protocol字符串（InfluxDB高效写入格式）
            line_protocol_lines = []
            for point in points:
                # 1. 处理Tag（转义特殊字符：逗号/空格/等号）
                tag_parts = []
                for tag_key, tag_val in point['tags'].items():
                    if tag_val:  # 跳过空Tag（避免无效索引）
                        escaped_val = tag_val.replace(',', r'\,').replace(' ', r'\ ').replace('=', r'\=')
                        tag_parts.append(f"{tag_key}={escaped_val}")
                tags_str = ','.join(tag_parts) if tag_parts else ''

                # 2. 处理Field（区分类型：字符串→加引号，布尔→t/f，数值→直接写）
                field_parts = []
                for field_key, field_val in point['fields'].items():
                    if isinstance(field_val, str):
                        # 字符串转义内部引号
                        escaped_val = field_val.replace('"', '\\"')
                        field_parts.append(f"{field_key}=\"{escaped_val}\"")
                    elif isinstance(field_val, bool):
                        field_parts.append(f"{field_key}={'t' if field_val else 'f'}")
                    elif isinstance(field_val, (int, float)):
                        field_parts.append(f"{field_key}={field_val}")
                fields_str = ','.join(field_parts)

                # 3. 拼接完整Line（格式：measurement,tags fields time）
                time_str = f" {point['time']}" if point.get('time') else ""
                if tags_str:
                    line = f"{point['measurement']},{tags_str} {fields_str}{time_str}"
                else:
                    line = f"{point['measurement']} {fields_str}{time_str}"
                line_protocol_lines.append(line)
            print(line_protocol_lines)

            # 4. 执行写入（使用Line Protocol协议）
            write_result = INFLUX_CLIENT.write(
                '\n'.join(line_protocol_lines),
                params={"db": "rapid_stream"},
                protocol='line'  # 明确指定协议
            )

            if write_result:
                write_time = time.time() - start_write
                logger.debug(f"批量写入成功 | 条数: {batch_size} | 耗时: {write_time:.2f}s")
                return batch_size
            else:
                logger.error(f"批量写入失败 | 条数: {batch_size} | InfluxDB返回异常")
                return 0

    except Exception as e:
        logger.error(f"批量写入异常 | 条数: {batch_size} | 错误: {str(e)}", exc_info=True)
        return 0



def fetch_and_process_stream_data_s1(api_url, measurement_name):
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
                print(data)
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
    fetch_and_process_stream_data_s1(
        "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1",
        "rapid_stream_status"
    )


def all_goose_stream_task():
    fetch_and_process_stream_data_s1(
        "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1",
        "goose_rapid_stream_status"
    )

def all_goose_stream_tasks2():
    fetch_and_process_stream_data(
        "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1",
        "goose_rapid_stream_status_test"
    )

all_goose_stream_tasks2()