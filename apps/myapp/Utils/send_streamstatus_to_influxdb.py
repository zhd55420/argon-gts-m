import asyncio
import datetime
import json
import logging
from influxdb import InfluxDBClient
import aiohttp  # 异步HTTP客户端

logger = logging.getLogger('streamstatus')

# 配置常量
CONFIG = {
    "influx": {
        "host": "15.204.133.239",
        "port": 8086,
        "database": "rapid_stream",
        "username": "uploader",
        "password": "bja!d7BB",
        "timeout": 15
    },
    "http": {
        "timeout": aiohttp.ClientTimeout(total=55),  # 总超时控制
        "chunk_size": 1024 * 512  # 512KB数据块
    }
}


# 异步Influx写入器（基于线程池）
async def async_write_points(client, points):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,  # 使用默认线程池
        lambda: client.write_points(points, batch_size=10000)
    )


async def async_fetch(session, api_url, measurement):
    """异步处理核心逻辑"""
    try:
        # 异步获取数据
        async with session.post(
                api_url,
                json={"streamRequest": {"source": ""}, "gooseStreamRequest": {"source": ""}},
                headers={"Content-Type": "application/json"}
        ) as res:
            res.raise_for_status()

            # 流式处理数据
            points = []
            async for chunk in res.content.iter_chunked(CONFIG["http"]["chunk_size"]):
                data_chunk = json.loads(chunk.decode())['data']

                # 并行处理数据转换
                timestamp = datetime.datetime.utcnow().replace(second=0, microsecond=0).isoformat() + "Z"
                batch = [{
                    "measurement": measurement,
                    "tags": {
                        "stream_id": str(item['streamResponse']['streamId']),
                        "source": str(item['streamResponse']['source']),
                        "signalType": str(item['streamResponse']['signalType'])
                    },
                    "time": timestamp,
                    "fields": {
                        "masterStatus": bool(item['streamStatus'].get('masterStreamStatus')),
                        "transcodeStatus": bool(item['streamStatus'].get('transcodeStreamStatus')),
                        "receiverStatus": bool(item['streamStatus'].get('channelReceiverStreamStatus')),
                        "bandWidth": item['streamStatus'].get('masterStreamStatus', {}).get('bw', 0),
                        "master_server_id": str(item['streamResponse']['masterServer']['serverId']),
                        "forward_server_id": str(item['streamResponse']['forwardServer']['serverId'])
                    }
                } for item in data_chunk]

                points.extend(batch)

                # 达到批次立即写入（非阻塞）
                if len(points) >= 5000:
                    await async_write_points(influx_client, points[:5000])
                    points = points[5000:]

            # 写入剩余数据
            if points:
                await async_write_points(influx_client, points)

    except Exception as e:
        logger.error(f"[{measurement}] 异步处理失败: {str(e)}")


# 入口函数
async def main(api_url, measurement):
    # 初始化连接
    influx_client = InfluxDBClient(**CONFIG["influx"])
    async with aiohttp.ClientSession(timeout=CONFIG["http"]["timeout"]) as session:
        await async_fetch(session, api_url, measurement)
    influx_client.close()


# 包装为同步函数供crontab调用
def all_stream_task():
    asyncio.run(main(
        "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1",
        "rapid_stream_status"
    ))


def all_goose_stream_task():
    asyncio.run(main(
        "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1",
        "goose_rapid_stream_status"
    ))