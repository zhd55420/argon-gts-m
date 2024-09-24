import logging



class VodQueryTool:
    def __init__(self, client, logger=None):
        self.client = client
        self.logger = logger or logging.getLogger('influxdb_query')

    def query_pm_bandwidth(self):
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("out_bw_bps") as "total_bandwidth" '
                'FROM ('
                '   SELECT first("out_bw_bps") AS "out_bw_bps"'
                '   FROM "autogen"."pm_server_stat" '
                '   WHERE "env_id" = \'PROD\' '
                '   AND "server_brand" = \'all\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            )
            self.logger.info(f"PM bandwidth Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_bandwidth'], reverse=True)
                total_bandwidth = sorted_points[2]['total_bandwidth'] / 1048576 / 1024  # 转换为 Gbps
            else:
                self.logger.warning("PM bandwidth:Not enough data points to determine the third highest bandwidth")
        except Exception as e:
            self.logger.error(f"PM bandwidth:Error querying bandwidth for PM bandwidth: {e}")
        self.logger.info(f"Total Bandwidth: {total_bandwidth} Gbps")
        return total_bandwidth

    def query_pm_users(self):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_user_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_user_count") AS "online_user_count"'
                '   FROM "autogen"."pm_server_stat" '
                '   WHERE "env_id" = \'PROD\' '
                '   AND "server_brand" = \'all\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            )

            self.logger.info(f"PM Users Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("PM Users:Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"PM Users:Error querying user count for PM servers: {e}")
        self.logger.info(f"PM Total Users: {total_user}")
        return total_user

    def query_pm_mobile_bandwidth(self):
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("out_bw_bps") as "total_bandwidth" '
                'FROM ('
                '   SELECT first("out_bw_bps") AS "out_bw_bps"'
                '   FROM "autogen"."pm_server_stat" '
                '   WHERE "dev_type" =~ /{}/ '
                '   AND "env_id" = \'PROD\' '
                '   AND "server_brand" = \'all\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            ).format("|".join(["MOBILE","mfc-mobile"]))

            self.logger.info(f"PM mobile bandwidth Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_bandwidth'], reverse=True)
                total_bandwidth = sorted_points[2]['total_bandwidth'] / 1048576 / 1024  # 转换为 Gbps
            else:
                self.logger.warning("PM mobile bandwidth:Not enough data points to determine the third highest bandwidth")
        except Exception as e:
            self.logger.error(f"PM mobile bandwidth:Error querying bandwidth for PM mobile bandwidth: {e}")
        self.logger.info(f"PM mobile Total Bandwidth: {total_bandwidth} Gbps")
        return total_bandwidth

    def query_pm_mobile_users(self):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_user_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_user_count") AS "online_user_count"'
                '   FROM "autogen"."pm_server_stat" '
                '   WHERE "dev_type" =~ /{}/ '
                '   AND "env_id" = \'PROD\' '
                '   AND "server_brand" = \'all\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            ).format("|".join(["MOBILE","mfc-mobile"]))

            self.logger.info(f"PM mobile Users Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("PM mobile Users:Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"PM mobile Users:Error querying user count for PM mobile Users: {e}")
        self.logger.info(f"PM mobile Total Users: {total_user}")
        return total_user

    def query_mrt_bandwidth(self):
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("out_bw_bps") as "total_bandwidth" '
                'FROM ('
                '   SELECT first("out_bw_bps") AS "out_bw_bps"'
                '   FROM "autogen"."mrt_server_stat" '
                '   WHERE "server_brand" = \'all\' '
                '   AND "env_id" = \'PROD\' '                
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            )
            self.logger.info(f"mrt bandwidth Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_bandwidth'], reverse=True)
                total_bandwidth = sorted_points[2]['total_bandwidth'] / 1048576 / 1024  # 转换为 Gbps
            else:
                self.logger.warning("mrt bandwidth:Not enough data points to determine the third highest bandwidth")
        except Exception as e:
            self.logger.error(f"mrt bandwidth:Error querying bandwidth for mrt bandwidth: {e}")
        self.logger.info(f"mrt Total Bandwidth: {total_bandwidth} Gbps")
        return total_bandwidth

    def query_mrt_users(self):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_user_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_user_count") AS "online_user_count"'
                '   FROM "autogen"."mrt_server_stat" '
                '   WHERE "server_brand" = \'all\' '
                '   AND "env_id" = \'PROD\' '                
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            )

            self.logger.info(f"mrt Users Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("mrt Users:Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"mrt Users:Error querying user count for mrt Users: {e}")
        self.logger.info(f"mrt Total Users: {total_user}")
        return total_user

    def query_mrt_mobile_bandwidth(self):
        total_bandwidth = 0
        try:
            query = (
                'SELECT sum("out_bw_bps") as "total_bandwidth" '
                'FROM ('
                '   SELECT first("out_bw_bps") AS "out_bw_bps"'
                '   FROM "autogen"."mrt_server_stat" '
                '   WHERE "dev_type" =~ /{}/ '
                '   AND "server_brand" = \'all\' '
                '   AND "env_id" = \'PROD\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            ).format("MOBILE")
            self.logger.info(f"mrt mobile bandwidth Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_bandwidth'], reverse=True)
                total_bandwidth = sorted_points[2]['total_bandwidth'] / 1048576 / 1024  # 转换为 Gbps
            else:
                self.logger.warning("mrt mobile bandwidth:Not enough data points to determine the third highest bandwidth")
        except Exception as e:
            self.logger.error(f"mrt mobile bandwidth:Error querying bandwidth for mrt mobile bandwidth: {e}")
        self.logger.info(f"mrt mobile Total Bandwidth: {total_bandwidth} Gbps")
        return total_bandwidth

    def query_mrt_mobile_users(self):
        total_user = 0
        try:
            query = (
                'SELECT sum("online_user_count") as "total_user" '
                'FROM ('
                '   SELECT first("online_user_count") AS "online_user_count"'
                '   FROM "autogen"."mrt_server_stat" '
                '   WHERE "dev_type" =~ /{}/ '
                '   AND "server_brand" = \'all\' '
                '   AND "env_id" = \'PROD\' '
                '   AND time >= now() - 10m '  # 时间范围调整
                '   GROUP BY time(1m), "server_id"'
                ') '
                'GROUP BY time(1m)'
            ).format("MOBILE")

            self.logger.info(f"mrt mobile user Query: {query}")
            result = self.client.query(query)
            points = [point for point in result.get_points()]

            # 汇总所有时间段的总和
            if len(points) >= 3:
                sorted_points = sorted(points, key=lambda x: x['total_user'], reverse=True)
                total_user = sorted_points[2]['total_user']
            else:
                self.logger.warning("mrt mobile user:Not enough data points to determine the third highest user count")
        except Exception as e:
            self.logger.error(f"mrt mobile user:Error querying user count for mrt mobile users: {e}")
        self.logger.info(f"mrt mobile Total Users: {total_user}")
        return total_user
