
import requests
import argparse
import json

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--id', action='store', dest='id', default='12345678')
    parser.add_argument('--ipaddr', action='store', dest='ipaddr', default='123.123.123.123')
    parser.add_argument('--ipport', action='store', dest='ipport', default='9999')
    parser.add_argument('-s', '--state', action='store', dest='state', default='registered')
    parser.add_argument('-p', '--protocol', action='store', dest='protocol', default='tcp')

    options = parser.parse_args()

    config = {}
    config['hardware_id'] = options.id
    config['ip_address'] = options.ipaddr
    config['port'] = options.ipport
    config['protocol'] = options.protocol
    config['state'] = options.state


    url = "http://192.168.1.118:8000/register/"
    headers = {'Content-type': 'application/json'}
    r = requests.post(url, data=json.dumps(config), headers=headers)
    
    print( 'Status: %d' % (r.status_code) )
