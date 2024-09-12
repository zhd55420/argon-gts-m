from influxdb import InfluxDBClient
import logging
from ..Configs import const_file   # 导入 const_file 模块


class InfluxDBQueryTool:
    def __init__(self, client, brand_config, logger=None):
        self.client = client
        self.brand_config = brand_config  # 品牌配置字典
        self.logger = logger or logging.getLogger('influxdb_query_error')

    def query_bandwidth(self, brand):
        try:
            if brand in self.brand_config['brands']['opt']:
                release_id = self.brand_config['brands']['opt'][brand]['release_id']
            elif brand in self.brand_config['brands']['spc']:
                release_id = self.brand_config['brands']['spc'][brand]['release_id']
            else:
                raise ValueError(f"Brand {brand} not found in configuration.")
            print(f"Brand: {brand}, Release ID: {release_id}")

            total_bandwidth = 0
            query = (
                'SELECT top("bandwidth_sum", 3) FROM "autogen"."aggregated_bandwidth_users" '
                'WHERE "server_brand" =~ /^{}/ AND time >= now() - 10m;'
            ).format(release_id)
            print(f"Executing query for bandwidth: {query}")
            result = self.client.query(query)
            last_set = [point for point in result.get_points()]
            if last_set:
                bandwidth = int(last_set[-1]['top']) / 1048576 / 1024
                total_bandwidth += bandwidth
        except Exception as e:
            self.logger.error(e)
            print(f"Error querying bandwidth for brand {brand}: {e}")
            raise
        return total_bandwidth

    def query_user(self, brand):
        try:
            if brand in self.brand_config['brands']['opt']:
                release_id = self.brand_config['brands']['opt'][brand]['release_id']
            elif brand in self.brand_config['brands']['spc']:
                release_id = self.brand_config['brands']['spc'][brand]['release_id']
            else:
                raise ValueError(f"Brand {brand} not found in configuration.")
            print(f"Brand: {brand}, Release ID: {release_id}")

            total_user = 0
            query = (
                'SELECT top("users_sum", 3) FROM "autogen"."aggregated_bandwidth_users" '
                'WHERE "server_brand" =~ /^{release_id}$/ AND time >= now() - 10m;'
            ).format(release_id=release_id)
            print(f"Executing query for users: {query}")
            result = self.client.query(query)
            last_set = [point for point in result.get_points()]
            if last_set:
                user = int(last_set[-1]['top'])
                total_user += user
        except Exception as e:
            self.logger.error(e)
            print(f"Error querying users for brand {brand}: {e}")
            raise
        return total_user



