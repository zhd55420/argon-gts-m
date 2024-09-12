import datetime
import json
import requests
from influxdb import InfluxDBClient
import logging

logger = logging.getLogger(__name__)


def fetch_and_process_stream_data(api_url, measurement_name):
    try:
        HEADERS = {
            "Content-Type": "application/json ;charset=utf-8 "
        }
        data_request = {
            "streamRequest": {
                "source": ""
            },
            "gooseStreamRequest": {
                "source": ""
            }
        }
        json_data = json.dumps(data_request)
        res = requests.post(api_url, data=json_data, headers=HEADERS)
        now_time = datetime.datetime.utcnow()
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

        client = InfluxDBClient(host='15.204.133.239', port=8086, database='rapid_stream', username='uploader',
                                password='bja!d7BB')
        client.write_points(points, database='rapid_stream',batch_size=1000)
        client.close()
        logger.info(f"Running Task for {measurement_name}")
    except Exception as e:
        logger.error(f"Error in Task for {measurement_name}: {str(e)}")


def all_stream_task():
    api_url = "http://3.15.111.189:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "rapid_stream_status")


def all_goose_stream_task():
    api_url = "http://54.237.33.107:2082/api/rapidStreamStatus/query/v1"
    fetch_and_process_stream_data(api_url, "goose_rapid_stream_status")
