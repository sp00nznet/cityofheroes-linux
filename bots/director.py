#!/usr/bin/env python3
"""Bot director: keeps BOTS copies of Ouroboros' TestClient.exe playing on the shard.
Each bot owns an account botN (made on first run). A bot that exits is restarted after RETRY s:
the first visit to a cold zone times out while the zone boots (~1 min under Wine), the retry gets in.
ponytail: one thread per bot, fine into the hundreds; the chat brain (LLM) plugs in later."""
import hashlib, os, random, signal, subprocess, sys, threading, time
import pymssql
from addaccount import game_hash

N = int(os.environ.get('BOTS', '5'))
MODES = os.environ.get('BOT_MODES', '+FIGHT +MOVE +CHAT +AUTOREZ').split()
RETRY = int(os.environ.get('BOT_RETRY', '60'))
# Bot accounts are real logins: derive their password from SA_PASSWORD rather than ship a known one.
PW = hashlib.sha256(('bots' + os.environ['SA_PASSWORD']).encode()).hexdigest()[:12]
DB = dict(server=os.environ.get('DB_HOST', 'db'), user='sa', password=os.environ['SA_PASSWORD'],
          database='cohauth', autocommit=True)
stop = threading.Event()

def ensure_account(name):
    with pymssql.connect(**DB) as c, c.cursor() as cur:
        cur.execute('SELECT 1 FROM dbo.user_account WHERE account=%s', name)
        if not cur.fetchall():
            cur.execute("""DECLARE @id INT = (SELECT ISNULL(MAX(uid),0)+1 FROM dbo.user_account);
INSERT INTO dbo.user_account (account, uid, forum_id, pay_stat) VALUES (%s, @id, @id, 1014);
INSERT INTO dbo.user_auth (account, password, salt, hash_type) VALUES (%s, CONVERT(BINARY(128), CONVERT(VARCHAR(128), %s)), 0, 1);
INSERT INTO dbo.user_data (uid, user_data) VALUES (@id, 0x00000000000000000000000000000000);
INSERT INTO dbo.user_server_group (uid, server_group_id) VALUES (@id, 1);""", (name, name, game_hash(name, PW)))
        else:  # keep the password in step with SA_PASSWORD
            cur.execute('UPDATE dbo.user_auth SET password=CONVERT(BINARY(128), CONVERT(VARCHAR(128), %s)), salt=0, hash_type=1 WHERE account=%s',
                        (game_hash(name, PW), name))

def character(name):
    """A finished character to resume, or a name that doesn't exist (TestClient then creates one).
    A creation cut short by a cold zone leaves a character with no class that can never be resumed."""
    with pymssql.connect(**DB) as c, c.cursor() as cur:
        # It holds the account's only slot, so drop it (it never got further than its Ents row) while offline.
        cur.execute("""DELETE e FROM cohdb.dbo.Ents e JOIN dbo.user_account a ON a.uid=e.AuthId
WHERE a.account=%s AND e.Class IS NULL AND ISNULL(e.Active,0)=0""", name)
        cur.execute("""SELECT TOP 1 e.Name FROM cohdb.dbo.Ents e JOIN dbo.user_account a ON a.uid=e.AuthId
WHERE a.account=%s AND e.Class IS NOT NULL ORDER BY e.ContainerId""", name)
        r = cur.fetchall()
    return r[0][0] if r else '~new'

def run_bot(n):
    name = f'bot{n}'
    ensure_account(name)
    while not stop.is_set():
        p = subprocess.Popen(['wine', 'TestClient.exe', '-authname', name, '-password', PW, '-auth', '127.0.0.1',
                              '-character', character(name), '-dontpause', '-nosharedmemory', *MODES],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t = time.time()
        while p.poll() is None and not stop.is_set(): time.sleep(1)
        if stop.is_set(): p.terminate(); return
        print(f'{name} exited {p.returncode} after {time.time()-t:.0f}s, retry in {RETRY}s', flush=True)
        stop.wait(RETRY + random.uniform(0, 10))

def main():
    signal.signal(signal.SIGTERM, lambda *a: stop.set())
    print(f'director: {N} bots, modes {" ".join(MODES)}', flush=True)
    threads = []
    for n in range(1, N + 1):
        threads.append(threading.Thread(target=run_bot, args=(n,), daemon=True)); threads[-1].start()
        if stop.wait(10): break   # stagger logins; each bot loads ~2 s of data then hits auth
    while not stop.is_set(): stop.wait(5)
    subprocess.run(['wineserver', '-k'])

if __name__ == '__main__':
    main()
