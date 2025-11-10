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
    
    data = awa
