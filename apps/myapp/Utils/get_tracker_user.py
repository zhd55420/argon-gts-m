import logging
from influxdb import InfluxDBClient
from ..Configs import const_file

class TrackerInfluxDBQueryTool:
    def __init__(self, client, tracker_config, logger=None):
        self.client = client
        self.tracker_config = tracker_config  # 配置字典
        self.logger = logger or logging.getLogger('influxdb_query_error')

    def query_bandwidth(self, tracker):
        server_code = self.tracker_config['Trackers'][tracker]['server_code']
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("bandwidth") FROM "tracker-server_stat" WHERE "server_id" =~ /{}/ and time > now() - 5m group by time(30s)'
            ).format(server_code)
            result = self.client.query(query)

            points = result.get_points()
            points_list = [point for point in points if point['sum'] is not None]
            points_list.sort(key=lambda x: x['sum'], reverse=True)
            total_bandwidth += points_list[2]['sum'] / (1024 * 1024 * 1024)  # 将带宽转换为 Gbps
        except Exception as e:
            self.logger.error(e)
        return total_bandwidth

    def query_user(self, tracker):
        server_code = self.tracker_config['Trackers'][tracker]['server_code']
        total_user = 0
        try:
            query = (
                'SELECT sum("online_count") FROM "tracker-server_stat" WHERE "server_id" =~ /{}/ and time > now() - 5m group by time(30s)'
            ).format(server_code)
            result = self.client.query(query)

            points = result.get_points()
            points_list = [point for point in points if point['sum'] is not None]
            points_list.sort(key=lambda x: x['sum'], reverse=True)
            total_user += points_list[2]['sum']
        except Exception as e:
            self.logger.error(e)
        return total_user

