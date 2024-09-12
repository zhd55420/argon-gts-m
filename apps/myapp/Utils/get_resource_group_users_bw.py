import logging
from influxdb import InfluxDBClient

class ResourceGroupQueryTool:
    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger or logging.getLogger('resource_group_query_tool')

    def query_prt_bandwidth(self, prt_server_ids):
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("send_bw_bps") as "total_bandwidth" '
                'FROM ('
                '   SELECT first("send_bw_bps") AS "send_bw_bps"'
                '   FROM "autogen"."prt_server_stat" '
                '   WHERE "server_id" =~ /{}/ '
                '   AND "server_brand" =~ /^all$/ '
                '   AND time >= now() - 30m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                '   fill(none)'
                ') '
                'GROUP BY time(1m)'
                'fill(none)'
            ).format("|".join(prt_server_ids))

            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_bandwidth'], reverse=True)
                total_bandwidth = sorted_points[2]['total_bandwidth'] / 1048576 / 1024  # 转换为 Gbps
            else:
                self.logger.warning("Not enough data points to determine the third highest bandwidth")
        except Exception as e:
            self.logger.error(f"Error querying bandwidth for PRT servers: {e}")
        self.logger.debug(f"Total Bandwidth: {total_bandwidth} Gbps")
        return total_bandwidth

    def query_prt_users(self, prt_server_ids):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_count") AS "online_count"'
                '   FROM "autogen"."prt_server_stat" '
                '   WHERE "server_id" =~ /{}/ '
                '   AND "server_brand" =~ /^all$/ '
                '   AND time >= now() - 30m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                '   fill(none)'
                ') '
                'GROUP BY time(1m)'
                'fill(none)'
            ).format("|".join(prt_server_ids))

            self.logger.debug(f"PRT Users Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]
            self.logger.debug(f"PRT Users Points: {points}")

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"Error querying user count for PRT servers: {e}")
        self.logger.debug(f"Total Users: {total_user}")
        return total_user

