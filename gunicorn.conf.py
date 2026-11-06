"""Use one CPU worker to limit model copies on Render Free."""
import os

bind = '0.0.0.0:' + os.environ.get('PORT', '10000')
workers = 1
worker_class = 'gthread'
threads = 2
timeout = 120
graceful_timeout = 30
accesslog = '-'
errorlog = '-'
# Load the models in the worker, without a second copy in the master process.
preload_app = False
