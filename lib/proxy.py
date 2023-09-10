import os
def enable_proxy(http_proxy,https_proxy):
    os.environ['http_proxy'] = http_proxy
    os.environ['https_proxy'] = https_proxy

def disable_proxy():
    del os.environ['http_proxy']
    del os.environ['https_proxy']
