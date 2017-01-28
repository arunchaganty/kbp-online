from boto.mturk.connection import MTurkConnection

def connect(host_str):
    SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
    HOST = 'mechanicalturk.amazonaws.com'
    if  host_str == 'sandbox':
        host = SANDBOX_HOST
    elif host_str == 'actual':
        host = HOST
        
    mtc = MTurkConnection(host = host)
    return mtc
