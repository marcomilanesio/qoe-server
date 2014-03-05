#!/usr/bin/python

def checkURL(url):
    """
    Check if param url is valid
    """
    import httplib
    import urlparse
    protocol = urlparse.urlsplit(url)[0]
    if protocol == '': #try adding http:// at beginning
        url = 'http://' + url
    
    protocol, host, path, query, fragment = urlparse.urlsplit(url)
    if protocol == "http":
        conntype = httplib.HTTPConnection
    elif protocol == "https":
        conntype = httplib.HTTPSConnection
    else:
        raise ValueError("unsupported protocol: " + protocol)

    conn = conntype(host)
    conn.request("HEAD", path)
    resp = conn.getresponse()
    conn.close()

    if resp.status < 400:
        return True

    return False
