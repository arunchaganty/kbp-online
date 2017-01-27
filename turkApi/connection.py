from boto.mturk.connection import MTurkConnection

def connect(host):
    SANDBOX_HOST = 'mechanicalturk.sandbox.amazonaws.com'
    HOST = 'mechanicalturk.amazonaws.com'
    if config.get('default', 'target') == 'sandbox':
        host = SANDBOX_HOST
    elif config.get('default', 'target') == 'actual':
        host = HOST
        
    mtc = MTurkConnection(host = host)
    return mtc
