#!/bin/bash
# One-shot: load Ouroboros schemas into the MSSQL container (idempotent: skips if cohauth exists).
case "$SA_PASSWORD" in ""|"ChangeMe!2026") echo "Set SA_PASSWORD in .env (not the example value)."; exit 1;; esac
export SQLCMDPASSWORD="$SA_PASSWORD"   # not -P: keeps it out of ps and survives odd characters
S="/opt/mssql-tools18/bin/sqlcmd -C -S db -U sa"
until $S -Q "select 1" >/dev/null 2>&1; do sleep 2; done
$S -h-1 -Q "set nocount on; select db_id('cohauth')" | grep -q NULL || { echo "dbs exist"; exit 0; }
for f in timeout cohauth cohacc cohauc cohchat insert; do echo "== $f"; $S -i /schemas/$f.sql; done
