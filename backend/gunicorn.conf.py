"""Single-origin application server; HTTPS terminates at the hosting ingress."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get('WEB_CONCURRENCY', '2'))
timeout = 30
accesslog = '-'
errorlog = '-'
# Keep query strings (which can contain search terms) out of access logs.
access_log_format = '%(h)s %(m)s %(U)s %(s)s %(L)s'
