#!/usr/bin/python

def checkURL(url):
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


if __name__ == '__main__':
    url = 'wwww.google.com'
    print checkURL(url)
