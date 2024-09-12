import logging
from influxdb import InfluxDBClient

class ResourceTrackerQueryTool:
    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger or logging.getLogger('resource_group_query_tool')

    def query_tracker_users(self, tracker_server_ids):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_count") AS "online_count" '
                '   FROM "tracker-server_stat" '
                '   WHERE "server_id" =~ /{}/ '
                '   AND time >= now() - 30m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            ).format("|".join(tracker_server_ids))

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

