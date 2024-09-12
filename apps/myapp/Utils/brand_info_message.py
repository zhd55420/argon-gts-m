# import datetime
#
#
# def get_livetv_message():
#     datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with DataApi() as data:
#         subject = "SZ TIME: {}".format(datetime_now)
#         try:
#             content =
#                       "TVE-WEB-PRT Bandwidth: {} Gbps\n" \
#                       "TVE-WEB-PRT Users: {}\n" \
#
#                 .format(
#                         )
#
#         except Exception as e:
#             info_message_logger.error('info message ERROR---{}'.format(e))
#             raise Exception(e)
#         return subject + '\n' + content