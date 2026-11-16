#!/bin/bash
# Same trick as the shard: run the EXE from a native dir, data symlinked back from the install.
set -e
R=/run/bots; mkdir -p $R; cp /coh/Server/TestClient.exe /coh/Server/*.dll $R/
for d in data piggs etc logs version.ini; do ln -sfn /coh/Server/$d $R/$d; done
# Small console font: each bot gets a Wine console window (see the shard's entrypoint).
wine reg add 'HKCU\Console' /v FontSize /t REG_DWORD /d 0x00060004 /f >/dev/null 2>&1
Xvfb :90 -screen 0 1600x1200x24 -nolisten tcp >/dev/null 2>&1 &
export DISPLAY=:90
# Wine binds its desktop to the first display it sees; starting before Xvfb is up breaks every window after.
until xwd -root -out /dev/null 2>/dev/null; do sleep 0.5; done
cd $R
exec python3 -u /bots/director.py
