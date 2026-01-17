import sys
import os

# Add parent directory to path to import server module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server import app

# Vercel serverless function handler
def handler(event, context):
    """Handle Vercel serverless function invocations"""
    # Import werkzeug for request handling
    from werkzeug.wrappers import Request, Response
    from io import BytesIO
    
    # Convert Vercel event to WSGI environ
    environ = {
        'REQUEST_METHOD': event.get('httpMethod', 'GET'),
        'SCRIPT_NAME': '',
        'PATH_INFO': event.get('path', '/'),
        'QUERY_STRING': event.get('queryStringParameters', ''),
        'CONTENT_TYPE': event.get('headers', {}).get('content-type', ''),
        'CONTENT_LENGTH': str(len(event.get('body', ''))),
        'SERVER_NAME': event.get('headers', {}).get('host', 'vercel.app'),
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': BytesIO(event.get('body', '').encode() if isinstance(event.get('body'), str) else event.get('body', b'')),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': False,
    }
    
    # Add headers to environ
    for key, value in event.get('headers', {}).items():
        key = 'HTTP_' + key.upper().replace('-', '_')
        environ[key] = value
    
    # Call Flask app
    response_data = []
    status_code = 500
    headers = []
    
    def start_response(status, response_headers):
        nonlocal status_code, headers
        status_code = int(status.split()[0])
        headers = response_headers
        return lambda x: response_data.append(x)
    
    app_response = app(environ, start_response)
    response_data.extend(app_response)
    
    # Convert response to Vercel format
    body = b''.join(response_data).decode('utf-8')
    
    return {
        'statusCode': status_code,
        'headers': dict(headers),
        'body': body
    }
