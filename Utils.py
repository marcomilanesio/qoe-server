#!/usr/bin/python

def check_url(url):
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


def order_numerical_keys(dic):
    tmp = map(int, dic.keys())
    tmp.sort()
    ordered_keys = map(str, tmp)
    return ordered_keys


def add_wildcard_to_url(url):
    if len(url) == 0:
        return '%'
    return '%'+url.strip()+'%'
