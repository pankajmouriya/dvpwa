"""
DVPWA - Damn Vulnerable Python Web App
Web request handlers with intentional security vulnerabilities
FOR SECURITY TESTING PURPOSES ONLY
"""

import os
import pickle
import subprocess
from aiohttp import web
from aiohttp_session import get_session
import xml.etree.ElementTree as ET
from sqli.models.user import User
import yaml
import hashlib


async def index(request):
    """Home page handler"""
    session = await get_session(request)
    username = session.get('username')
    
    return web.Response(
        text=f"<h1>Welcome {username}!</h1>",
        content_type='text/html'
    )


async def login(request):
    """
    VULNERABLE: Multiple security issues
    - SQL Injection
    - Session fixation
    - Timing attacks
    """
    if request.method == 'POST':
        data = await request.post()
        username = data.get('username')
        password = data.get('password')
        
        # VULNERABLE: SQL Injection - string concatenation
        conn = request.app['db']
        async with conn.cursor() as cur:
            query = f"""
                SELECT * FROM users 
                WHERE username = '{username}' AND pwd_hash = MD5('{password}')
            """
            await cur.execute(query)
            user = await cur.fetchone()
        
        if user:
            session = await get_session(request)
            # VULNERABLE: Session fixation - not regenerating session ID
            session['username'] = username
            session['user_id'] = user[0]
            return web.Response(text="Login successful!")
        else:
            return web.Response(text="Login failed!")
    
    return web.Response(
        text='<form method="post"><input name="username"><input name="password" type="password"><button>Login</button></form>',
        content_type='text/html'
    )


async def search_users(request):
    """
    VULNERABLE: SQL Injection in search functionality
    """
    search = request.query.get('q', '')
    
    conn = request.app['db']
    async with conn.cursor() as cur:
        # VULNERABLE: SQL Injection with LIKE clause
        query = f"SELECT username, first_name, last_name FROM users WHERE username LIKE '%{search}%'"
        await cur.execute(query)
        results = await cur.fetchall()
    
    # VULNERABLE: XSS - no output escaping
    html = "<h2>Search Results</h2><ul>"
    for user in results:
        html += f"<li>{user[0]} - {user[1]} {user[2]}</li>"
    html += "</ul>"
    
    return web.Response(text=html, content_type='text/html')


async def profile(request):
    """
    VULNERABLE: Insecure Direct Object Reference (IDOR)
    """
    # VULNERABLE: No authorization check
    user_id = request.query.get('id')
    
    conn = request.app['db']
    async with conn.cursor() as cur:
        # VULNERABLE: SQL Injection via integer parameter
        query = f"SELECT * FROM users WHERE id = {user_id}"
        await cur.execute(query)
        user = await cur.fetchone()
    
    if user:
        # VULNERABLE: Exposing sensitive data (password hash)
        return web.json_response({
            'id': user[0],
            'username': user[1],
            'first_name': user[2],
            'last_name': user[3],
            'pwd_hash': user[4],  # Should never expose this!
            'is_admin': user[5]
        })
    
    return web.Response(status=404)


async def update_profile(request):
    """
    VULNERABLE: Mass assignment vulnerability
    """
    session = await get_session(request)
    user_id = session.get('user_id')
    
    data = await request.post()
    
    conn = request.app['db']
    async with conn.cursor() as cur:
        # VULNERABLE: Mass assignment - allows updating any field including is_admin
        for field, value in data.items():
            query = f"UPDATE users SET {field} = '{value}' WHERE id = {user_id}"
            await cur.execute(query)
    
    return web.Response(text="Profile updated!")


async def upload_avatar(request):
    """
    VULNERABLE: Unrestricted file upload
    """
    session = await get_session(request)
    username = session.get('username')
    
    data = await request.post()
    avatar = data['avatar']
    
    # VULNERABLE: No file type validation
    # VULNERABLE: Path traversal possible
    filename = avatar.filename
    filepath = f"/var/www/uploads/{username}/{filename}"
    
    # Create directory if not exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # VULNERABLE: Writing user-controlled content
    with open(filepath, 'wb') as f:
        f.write(avatar.file.read())
    
    return web.Response(text=f"Avatar uploaded: {filename}")


async def download_file(request):
    """
    VULNERABLE: Path traversal vulnerability
    """
    filename = request.query.get('file')
    
    # VULNERABLE: No path sanitization
    filepath = f"/var/www/uploads/{filename}"
    
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        return web.Response(
            body=content,
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )
    except FileNotFoundError:
        return web.Response(status=404)


async def execute_command(request):
    """
    VULNERABLE: OS Command Injection
    """
    if request.method == 'POST':
        data = await request.post()
        command = data.get('cmd')
        
        # VULNERABLE: Direct command execution
        result = os.popen(command).read()
        
        return web.Response(text=f"<pre>{result}</pre>", content_type='text/html')
    
    return web.Response(
        text='<form method="post"><input name="cmd"><button>Execute</button></form>',
        content_type='text/html'
    )


async def generate_report(request):
    """
    VULNERABLE: Command Injection via subprocess
    """
    report_type = request.query.get('type', 'summary')
    user_id = request.query.get('user_id', '1')
    
    # VULNERABLE: Command injection
    cmd = f"python generate_report.py --type {report_type} --user {user_id}"
    result = subprocess.call(cmd, shell=True, capture_output=True)
    
    return web.Response(text="Report generated!")


async def import_config(request):
    """
    VULNERABLE: Insecure deserialization (YAML)
    """
    data = await request.post()
    config_data = data.get('config')
    
    # VULNERABLE: Unsafe YAML loading
    config = yaml.load(config_data, Loader=yaml.Loader)
    
    return web.json_response({'status': 'Config imported', 'config': config})


async def parse_xml(request):
    """
    VULNERABLE: XML External Entity (XXE) Injection
    """
    data = await request.post()
    xml_data = data.get('xml')
    
    # VULNERABLE: XML parsing without disabling external entities
    root = ET.fromstring(xml_data)
    
    result = {
        'tag': root.tag,
        'text': root.text,
        'attrib': root.attrib
    }
    
    return web.json_response(result)


async def serialize_session(request):
    """
    VULNERABLE: Insecure deserialization (pickle)
    """
    session = await get_session(request)
    
    # VULNERABLE: Using pickle for serialization
    serialized = pickle.dumps(session)
    
    return web.Response(
        body=serialized,
        content_type='application/octet-stream'
    )


async def deserialize_session(request):
    """
    VULNERABLE: Insecure deserialization (pickle)
    """
    data = await request.read()
    
    # VULNERABLE: Unpickling untrusted data
    session_data = pickle.loads(data)
    
    return web.json_response(session_data)


async def redirect(request):
    """
    VULNERABLE: Open Redirect
    """
    url = request.query.get('url')
    
    # VULNERABLE: No URL validation
    return web.HTTPFound(url)


async def api_token(request):
    """
    VULNERABLE: Weak token generation
    """
    import random
    
    # VULNERABLE: Using random instead of secrets
    token = ''.join([str(random.randint(0, 9)) for _ in range(20)])
    
    return web.json_response({'token': token})


async def reset_password(request):
    """
    VULNERABLE: Predictable password reset tokens
    """
    data = await request.post()
    email = data.get('email')
    
    # VULNERABLE: Predictable token
    reset_token = hashlib.md5(email.encode()).hexdigest()
    
    # Store reset token (vulnerable implementation)
    return web.Response(text=f"Reset link: /reset?token={reset_token}")


async def admin_panel(request):
    """
    VULNERABLE: Broken access control
    """
    session = await get_session(request)
    
    # VULNERABLE: Checking only session, not actual permissions
    if 'user_id' in session:
        return web.Response(
            text="<h1>Admin Panel</h1><p>All users can access this!</p>",
            content_type='text/html'
        )
    
    return web.Response(status=403)


# VULNERABLE: Hardcoded credentials
DATABASE_PASSWORD = "admin123"
API_SECRET_KEY = "sk-1234567890abcdef"
JWT_SECRET = "my-jwt-secret-key"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"


def eval_expression(request):
    """
    VULNERABLE: Code injection via eval
    """
    expr = request.query.get('expr', '1+1')
    
    # DANGEROUS: Never use eval on user input
    result = eval(expr)
    
    return web.Response(text=f"Result: {result}")


# Route setup (to be imported in routes.py)
def setup_routes(app):
    """Setup all routes"""
    app.router.add_get('/', index)
    app.router.add_route('*', '/login', login)
    app.router.add_get('/search', search_users)
    app.router.add_get('/profile', profile)
    app.router.add_post('/profile/update', update_profile)
    app.router.add_post('/upload', upload_avatar)
    app.router.add_get('/download', download_file)
    app.router.add_route('*', '/exec', execute_command)
    app.router.add_get('/report', generate_report)
    app.router.add_post('/import', import_config)
    app.router.add_post('/xml', parse_xml)
    app.router.add_get('/serialize', serialize_session)
    app.router.add_post('/deserialize', deserialize_session)
    app.router.add_get('/redirect', redirect)
    app.router.add_get('/token', api_token)
    app.router.add_post('/reset', reset_password)
    app.router.add_get('/admin', admin_panel)
    app.router.add_get('/eval', eval_expression)
