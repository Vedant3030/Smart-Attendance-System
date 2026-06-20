#!/usr/bin/env python3
"""Simple health-check script for the Attendance API.

Usage: python scripts/check_health.py [--url URL]
Exits with code 0 when health endpoint returns status OK, otherwise non-zero.
"""
import sys
import argparse
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8000/health')
    args = parser.parse_args()

    try:
        with urlopen(args.url, timeout=3) as resp:
            body = resp.read().decode('utf-8')
            if 'ok' in body.lower():
                print('healthy')
                return 0
            else:
                print('unhealthy:', body)
                return 2
    except HTTPError as e:
        print('http error:', e)
        return 3
    except URLError as e:
        print('url error:', e)
        return 3
    except Exception as e:
        print('error:', e)
        return 4


if __name__ == '__main__':
    sys.exit(main())
