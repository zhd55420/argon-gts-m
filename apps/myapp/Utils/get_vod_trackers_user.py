import logging
from influxdb import InfluxDBClient

class VodTrackerQueryTool:
    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger or logging.getLogger('vod_query_tool')

    def query_tracker_users(self):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_user_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_user_count") AS "online_user_count" '
                '   FROM "tracker-server_stat" '
                '   WHERE "env_id" = \'PROD\'  '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            )

            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"Error querying user count for Tracker servers: {e}")
        self.logger.debug(f"Total Users: {total_user}")
        return total_user
