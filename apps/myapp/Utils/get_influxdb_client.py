from django.conf import settings
from influxdb import InfluxDBClient

def get_livetv_influxdb_client():
    config = settings.LIVE_INFLUXDB_CONFIG
    client = InfluxDBClient(
        host=config['HOST'],
        port=config['PORT'],
        database=config['DATABASE'],
        username=config.get('USERNAME', ''),
        password=config.get('PASSWORD', '')
    )
    return client

def get_vod_influxdb_client():
    config = settings.VOD_INFLUXDB_CONFIG
    client = InfluxDBClient(
        host=config['HOST'],
        port=config['PORT'],
        database=config['DATABASE'],
        username=config.get('USERNAME', ''),
        password=config.get('PASSWORD', '')
    )
    return client


