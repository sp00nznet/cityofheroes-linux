#!/usr/bin/env python3
"""Print SQL that creates a CoH auth account, compatible with CoHDBTools10 addAccount.php
(the hash algorithm reimplemented for compatibility; no code copied).
usage: addaccount.py NAME PASSWORD | docker compose exec -T db /opt/mssql-tools18/bin/sqlcmd -C -U sa -P "$SA_PASSWORD" -d cohauth"""
import hashlib, sys, zlib

def game_hash(name, pw):
    a = '%08x' % zlib.adler32(name.lower().encode())
    a = a[6:8] + a[4:6] + a[2:4] + a[0:2]          # byte-swapped hex, as in the PHP
    return hashlib.sha512((pw + a).encode()).hexdigest()

def sql(name, pw):
    if not (name.isascii() and name.isalnum()) or not (8 <= len(pw) <= 16) or "'" in pw:
        sys.exit('name must be alphanumeric, password 8-16 chars without quotes')
    return f"""SET NOCOUNT ON; DECLARE @id INT = (SELECT ISNULL(MAX(uid),0)+1 FROM dbo.user_account);
INSERT INTO dbo.user_account (account, uid, forum_id, pay_stat) VALUES ('{name}', @id, @id, 1014);
INSERT INTO dbo.user_auth (account, password, salt, hash_type) VALUES ('{name}', CONVERT(BINARY(128),'{game_hash(name, pw)}'), 0, 1);
INSERT INTO dbo.user_data (uid, user_data) VALUES (@id, 0x00000000000000000000000000000000);
INSERT INTO dbo.user_server_group (uid, server_group_id) VALUES (@id, 1);
SELECT uid, account FROM dbo.user_account WHERE account='{name}';"""

if __name__ == '__main__':
    assert len(game_hash('a', 'b')) == 128
    print(sql(sys.argv[1], sys.argv[2]))
