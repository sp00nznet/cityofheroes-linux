#!/bin/bash
# Points Ouroboros's LocalDB connection strings at the db container, then starts the shard.
set -e
# MS ODBC Driver 17 (x86 dll from Ouroboros's own x64 MSI) behaves like Windows; FreeTDS misreports nvarchar(max).
if ! wine reg query 'HKLM\Software\Wow6432Node\ODBC\ODBCINST.INI\ODBC Drivers' 2>/dev/null | grep -q 'Driver 17'; then
  echo "installing MS ODBC Driver 17 into wine prefix"
  wine msiexec /i 'Z:\coh\Setup\SQLInstall\msodbcsql17x64.msi' IACCEPTMSODBCSQLLICENSETERMS=YES /qn
fi
CS="Driver={ODBC Driver 17 for SQL Server};Server=${DB_HOST:-db},1433;UID=sa;PWD=${SA_PASSWORD};"
for f in data/server/db/servers.cfg data/server/db/account_server.cfg data/server/db/auction_server.cfg \
         data/server/db/chat_server.cfg; do
  sed -i -E "s#^(\s*)SqlLogin .*#\1SqlLogin \"$CS\"#" "$f"
done
sed -i -E "s#^connectionString = .*#connectionString = \"${CS}Database=cohauth;\"#" etc/config.txt
mkdir -p logs
# MapServers report gethostbyname(own hostname) to DBServer, which hands that IP to clients.
# Inside Docker that's the unreachable container IP, so pin our hostname to the address clients use.
IP=${COH_IP:-127.0.0.1}
if [ "${PIN_HOSTNAME:-1}" = 1 ]; then { grep -vw "$(hostname)" /etc/hosts; echo "$IP $(hostname)"; } > /tmp/hosts && cat /tmp/hosts > /etc/hosts; fi
sed -i -E "s/^AdvertisedIp .*/AdvertisedIp $IP/" data/server/db/servers.cfg
# Wine's odbc32 can't map ANSI calls onto the Unicode-only MS driver; Windows' own driver manager can.
# Supply odbc32.dll + odbcint.dll from any Windows box's SysWOW64 in ./winodbc (not redistributable, so not baked in).
if [ -f /winodbc/odbc32.dll ]; then
  cp /winodbc/odbc32.dll /winodbc/odbcint.dll /wine/drive_c/windows/syswow64/
  export WINEDLLOVERRIDES="odbc32=n"
else echo "WARN: no ./winodbc/odbc32.dll - DBServer schema sync will fail under Wine's odbc32"; fi
# ponytail: Wine maps PE images as zeros from Windows-drive bind mounts (Docker Desktop/WSL 9p).
# Run binaries from a native dir; data dirs are symlinked back (plain reads work fine).
R=/run/coh; mkdir -p $R; cp *.exe *.dll $R/
for d in data piggs etc logs missionserver beaconizer version.ini; do ln -sfn /coh/Server/$d $R/$d; done
bash /patch.sh $R
python3 /patch_odbc.py $R/*.exe
python3 /patch_idle.py $R/*.exe
# ServerMonitor is a GUI status window (~1 core under Wine polling files); stub it unless asked for.
[ "${SERVERMONITOR:-0}" = 1 ] || cp /wine/drive_c/windows/syswow64/hostname.exe $R/ServerMonitor.exe
# Servers ask for a 9999-line console; Wine's windowed conhost backs the whole buffer with a bitmap
# (~560 MB each at the default font). A 4x6 font shrinks it ~4x (1x1 hangs the servers).
wine reg add 'HKCU\Console' /v FontSize /t REG_DWORD /d 0x00060004 /f >/dev/null 2>&1
cd $R
for exe in AuthServer DBServer Launcher; do
  echo "starting $exe"; xvfb-run -a wine $exe.exe > logs/$exe.wine.log 2>&1 &
  sleep 5
done
tail -F logs/*.wine.log
