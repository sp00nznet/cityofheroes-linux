#!/usr/bin/env python3
"""Shard admin panel: accounts (create, password, ban), characters (access level), shard status.
Stdlib http.server + pymssql. HTTP Basic auth (admin / PANEL_PASSWORD). Bound to localhost by compose.
ponytail: single-threaded, no sessions or templates; a small shard's admin is one person."""
import base64, hmac, html, os, socket, sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse, quote
import pymssql
from addaccount import game_hash

PW = os.environ.get('PANEL_PASSWORD', '')
if len(PW) < 8:
    sys.exit('Set PANEL_PASSWORD (8+ chars) in .env')
DB = dict(server=os.environ.get('DB_HOST', 'db'), user='sa', password=os.environ['SA_PASSWORD'], autocommit=True)
SHARD = os.environ.get('SHARD_HOST', 'coh')
ACCESS = {0: 'player', 1: 'helper', 2: 'GM', 3: 'GM+', 9: 'dev', 10: 'admin', 11: 'super admin'}

def q(sql, *args, db='cohauth'):
    with pymssql.connect(database=db, **DB) as c, c.cursor(as_dict=True) as cur:
        cur.execute(sql, args or None)
        return cur.fetchall() if cur.description else []

def valid(name, pw):
    if not (name.isascii() and name.isalnum() and 1 <= len(name) <= 14): return 'Name: letters and digits, up to 14.'
    if not 8 <= len(pw) <= 16: return 'Password: 8 to 16 characters.'

def create(name, pw):
    if (e := valid(name, pw)): return e
    if q('SELECT 1 x FROM dbo.user_account WHERE account=%s', name): return f'{name} already exists.'
    q("""DECLARE @id INT = (SELECT ISNULL(MAX(uid),0)+1 FROM dbo.user_account);
INSERT INTO dbo.user_account (account, uid, forum_id, pay_stat) VALUES (%s, @id, @id, 1014);
INSERT INTO dbo.user_auth (account, password, salt, hash_type) VALUES (%s, CONVERT(BINARY(128), CONVERT(VARCHAR(128), %s)), 0, 1);
INSERT INTO dbo.user_data (uid, user_data) VALUES (@id, 0x00000000000000000000000000000000);
INSERT INTO dbo.user_server_group (uid, server_group_id) VALUES (@id, 1);""", name, name, game_hash(name, pw))
    return f'Created {name}.'

def set_password(name, pw):
    if (e := valid(name, pw)): return e
    q('UPDATE dbo.user_auth SET password=CONVERT(BINARY(128), CONVERT(VARCHAR(128), %s)), salt=0, hash_type=1 WHERE account=%s', game_hash(name, pw), name)
    return f'Password set for {name}.'

def port_open(host, port):
    try: socket.create_connection((host, port), 1).close(); return True
    except OSError: return False

CSS = """:root{--bg:#f6f7f9;--fg:#1b1f24;--card:#fff;--line:#d9dde3;--mute:#5d6672;--acc:#2456c9;--bad:#b3261e;--ok:#1d7a3a}
@media (prefers-color-scheme:dark){:root{--bg:#121417;--fg:#e6e8eb;--card:#1b1e23;--line:#2c3138;--mute:#98a1ad;--acc:#7aa2ff;--bad:#ff7b72;--ok:#56d364}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif}
main{max-width:980px;margin:0 auto;padding:16px}h1{font-size:20px}h2{font-size:16px;margin-top:28px}
a{color:var(--acc)}nav a{margin-right:14px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;margin:12px 0;overflow-x:auto}
table{border-collapse:collapse;width:100%}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th{color:var(--mute);font-weight:600}input,select,button{font:inherit;padding:4px 8px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--fg)}
button{background:var(--acc);color:#fff;border:0;cursor:pointer}button.bad{background:var(--bad)}form{display:inline}
.ok{color:var(--ok)}.bad{color:var(--bad)}.msg{padding:8px 12px;border-left:3px solid var(--acc);background:var(--card)}.mute{color:var(--mute)}"""

def page(title, body, msg=''):
    m = f'<p class="msg">{html.escape(msg)}</p>' if msg else ''
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>{CSS}</style></head><body><main>
<nav><a href="/">Status</a><a href="/accounts">Accounts</a></nav><h1>{html.escape(title)}</h1>{m}{body}</main></body></html>"""

def status():
    rows = [('AuthServer (2104)', port_open(SHARD, 2104)), ('DBServer (6997)', port_open(SHARD, 6997))]
    try:
        n = q('SELECT COUNT(*) n FROM dbo.user_account')[0]['n']
        c = q('SELECT COUNT(*) n, SUM(CASE WHEN Active>0 THEN 1 ELSE 0 END) online FROM dbo.Ents', db='cohdb')[0]
        rows.append(('MSSQL', True))
    except Exception: n, c = '?', {'n': '?', 'online': '?'}; rows.append(('MSSQL', False))
    t = ''.join(f'<tr><td>{k}</td><td class="{"ok" if v else "bad"}">{"up" if v else "down"}</td></tr>' for k, v in rows)
    return page('Shard status', f"""<div class="card"><table>{t}</table></div>
<div class="card">{n} accounts · {c['n']} characters · {c['online'] or 0} online</div>""")

def accounts(msg=''):
    rows = q("""SELECT a.account, a.uid, a.block_flag, a.last_login, a.last_ip,
  (SELECT COUNT(*) FROM cohdb.dbo.Ents e WHERE e.AuthId=a.uid) chars FROM dbo.user_account a ORDER BY a.uid""")
    t = ''
    for r in rows:
        a = html.escape(r['account']); blocked = r['block_flag'] != 0
        t += f"""<tr><td><a href="/account?name={quote(r['account'])}">{a}</a></td><td>{r['uid']}</td><td>{r['chars']}</td>
<td>{html.escape(str(r['last_login'] or '—'))}</td><td>{html.escape(r['last_ip'] or '—')}</td>
<td>{'<span class="bad">banned</span>' if blocked else 'ok'}</td>
<td><form method="post" action="/password"><input type="hidden" name="name" value="{a}"><input name="pw" type="password" placeholder="new password" minlength="8" maxlength="16" required> <button>Set</button></form>
<form method="post" action="/block"><input type="hidden" name="name" value="{a}"><input type="hidden" name="on" value="{0 if blocked else 1}"><button class="{'' if blocked else 'bad'}">{'Unban' if blocked else 'Ban'}</button></form></td></tr>"""
    return page('Accounts', f"""<div class="card"><form method="post" action="/create">
<input name="name" placeholder="account name" maxlength="14" required> <input name="pw" type="password" placeholder="password (8-16)" minlength="8" maxlength="16" required> <button>Create account</button></form></div>
<div class="card"><table><tr><th>Account</th><th>uid</th><th>Chars</th><th>Last login</th><th>Last IP</th><th>State</th><th></th></tr>{t}</table></div>""", msg)

def account(name, msg=''):
    acc = q('SELECT uid FROM dbo.user_account WHERE account=%s', name)
    if not acc: return page('Not found', '', f'No account {name}.')
    rows = q("""SELECT e.ContainerId id, e.Name, ISNULL(e.Level,0)+1 lvl, c.Name cls, o.Name org, e.AccessLevel al, e.Active, e.LastActive
FROM dbo.Ents e LEFT JOIN dbo.Attributes c ON c.Id=e.Class LEFT JOIN dbo.Attributes o ON o.Id=e.Origin WHERE e.AuthId=%s ORDER BY e.ContainerId""", acc[0]['uid'], db='cohdb')
    t = ''
    for r in rows:
        opts = ''.join(f'<option value="{k}"{" selected" if (r["al"] or 0) == k else ""}>{k} {v}</option>' for k, v in ACCESS.items())
        cls = (r['cls'] or '—').replace('class_', '')
        t += f"""<tr><td>{html.escape(r['Name'] or '—')}</td><td>{r['lvl']}</td><td>{html.escape(cls)}</td><td>{html.escape(r['org'] or '—')}</td>
<td>{'<span class="ok">online</span>' if r['Active'] else html.escape(str(r['LastActive'] or '—'))}</td>
<td><form method="post" action="/access"><input type="hidden" name="name" value="{html.escape(name)}"><input type="hidden" name="id" value="{r['id']}">
<select name="level">{opts}</select> <button>Set</button></form></td></tr>"""
    return page(f'Account {name}', f"""<div class="card"><table><tr><th>Character</th><th>Level</th><th>Class</th><th>Origin</th><th>Last on</th><th>Access level</th></tr>{t}</table>
<p class="mute">Access level changes apply next time the character logs in; set them while it's offline.</p></div>""", msg)

class H(BaseHTTPRequestHandler):
    def authed(self):
        a = self.headers.get('Authorization', '')
        ok = a.startswith('Basic ') and hmac.compare_digest(base64.b64decode(a[6:] + '==').decode(errors='replace'), f'admin:{PW}')
        if not ok:
            self.send_response(401); self.send_header('WWW-Authenticate', 'Basic realm="coh panel"'); self.end_headers()
        return ok
    def send(self, body, code=200):
        b = body.encode(); self.send_response(code)
        self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(b)))
        self.send_header('X-Frame-Options', 'DENY'); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if not self.authed(): return
        u = urlparse(self.path); a = parse_qs(u.query)
        try:
            if u.path == '/': self.send(status())
            elif u.path == '/accounts': self.send(accounts())
            elif u.path == '/account': self.send(account(a.get('name', [''])[0]))
            else: self.send(page('Not found', ''), 404)
        except Exception as e: self.send(page('Error', '', f'{type(e).__name__}: {e}'), 500)
    def do_POST(self):
        if not self.authed(): return
        # CSRF: Basic auth rides along on cross-site posts, so require a same-origin Origin header.
        o = self.headers.get('Origin')
        if not o or urlparse(o).netloc != self.headers.get('Host'): return self.send(page('Refused', '', 'Cross-site request.'), 403)
        f = {k: v[0] for k, v in parse_qs(self.rfile.read(int(self.headers.get('Content-Length', 0))).decode()).items()}
        name = f.get('name', '')
        try:
            if self.path == '/create': self.send(accounts(create(name, f.get('pw', ''))))
            elif self.path == '/password': self.send(accounts(set_password(name, f.get('pw', ''))))
            elif self.path == '/block':
                q('UPDATE dbo.user_account SET block_flag=%s WHERE account=%s', int(f.get('on') == '1'), name)
                self.send(accounts(f"{'Banned' if f.get('on') == '1' else 'Unbanned'} {name}."))
            elif self.path == '/access':
                lvl = int(f.get('level', 0))
                if lvl not in ACCESS: raise ValueError('bad level')
                q('UPDATE dbo.Ents SET AccessLevel=%s WHERE ContainerId=%s', lvl, int(f.get('id', 0)), db='cohdb')
                self.send(account(name, f'Access level set to {lvl} ({ACCESS[lvl]}).'))
            else: self.send(page('Not found', ''), 404)
        except Exception as e: self.send(page('Error', '', f'{type(e).__name__}: {e}'), 500)
    def log_message(self, fmt, *a): sys.stderr.write('panel: ' + fmt % a + '\n')

if __name__ == '__main__':
    print('panel on :8080', flush=True)
    HTTPServer(('0.0.0.0', 8080), H).serve_forever()
