#!/bin/bash
# Xvfb + openbox + VNC/noVNC, then the client pointed at the shard (shares its network: localhost).
export DISPLAY=:1
Xvfb :1 -screen 0 1280x800x24 & sleep 2
openbox & x11vnc -display :1 -localhost -forever -shared -nopw -quiet -rfbport 5900 &
websockify --web /usr/share/novnc 6080 localhost:5900 &
# ponytail: same Wine-mount workaround as the server: run the exe from a native dir, data symlinked.
C=/run/client; mkdir -p $C; cp /client/*.exe /client/*.dll $C/
for d in piggs ouro version.ini; do ln -sfn /client/$d $C/$d; done
cd $C
export WINEDEBUG=${CLIENT_WINEDEBUG:-err+all,fixme-all}
while true; do
  wine Ouroboros.exe -auth ${COH_IP:-127.0.0.1} -patchdir ouro -noversioncheck -fullscreen 0 -screen 1280 720
  echo "client exited, restarting in 5s"; sleep 5
done
