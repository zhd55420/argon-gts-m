import logging
from influxdb import InfluxDBClient
from ..Configs import const_file

class TrackerInfluxDBQueryTool:
    def __init__(self, client, tracker_config, logger=None):
        self.client = client
        self.tracker_config = tracker_config  # 配置字典
        self.logger = logger or logging.getLogger('influxdb_query')

    def query_bandwidth(self, tracker):
        server_code = self.tracker_config['Trackers'][tracker]['server_code']
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("bandwidth") FROM "tracker-server_stat" WHERE "server_id" =~ /{}/ and time > now() - 5m group by time(30s)'
            ).format(server_code)
            result = self.client.query(query)
            self.logger.info(f"tracker bandwidth Query: {query}")
            points = result.get_points()
            points_list = [point for point in points if point['sum'] is not None]
            points_list.sort(key=lambda x: x['sum'], reverse=True)
            total_bandwidth += points_list[2]['sum'] / (1024 * 1024 * 1024)  # 将带宽转换为 Gbps
            self.logger.info(f"tracker Total bandwidth: {total_bandwidth}")
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

            self.logger.info(f"tracker users Query: {query}")
            points = result.get_points()
            points_list = [point for point in points if point['sum'] is not None]
            points_list.sort(key=lambda x: x['sum'], reverse=True)
            total_user += points_list[2]['sum']
            self.logger.info(f"tracker Total users: {total_user}")
        except Exception as e:
            self.logger.error(e)
        return total_user

