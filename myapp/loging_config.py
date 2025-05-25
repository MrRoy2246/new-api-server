# from elasticsearch import Elasticsearch
# import logging

# class ElasticsearchHandler(logging.Handler):
#     def __init__(self, hosts=None, index='django-logs'):
#         super().__init__()
#         self.es = Elasticsearch("http://192.168.1.147:9200", verify_certs=False)
#         self.index = index

#     def emit(self, record):
#         try:
#             log_entry = self.format_record(record)
#             print("💡 Sending log to Elasticsearch:", log_entry)  # 👈 Add this
#             self.es.index(index=self.index, body=log_entry)
#         except Exception as e:
#             # Avoid crashing Django if logging fails
#             print("Elasticsearch logging failed:", e)

#     def format_record(self, record):
#         return {
#             'message': record.getMessage(),
#             'level': record.levelname,
#             'logger': record.name,
#             'pathname': record.pathname,
#             'lineno': record.lineno,
#             'timestamp': record.created,
#         }
