# myapp/utils.py
import threading

_thread_locals = threading.local()

def set_request_token(token):
    _thread_locals.token = token

def get_request_token():
    return getattr(_thread_locals, 'token', None)

def clear_request_token():
    _thread_locals.token = None
