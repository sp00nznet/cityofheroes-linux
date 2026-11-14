# CoH client under Wine 11 on a virtual X display, viewable in a browser via noVNC (port 6080).
FROM coh-server
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      x11vnc novnc websockify xvfb openbox mesa-utils imagemagick libgl1-mesa-dri libgl1-mesa-dri:i386 libglx-mesa0 libglx-mesa0:i386 libgl1 libgl1:i386 libegl1 libegl1:i386 libegl-mesa0 libegl-mesa0:i386 && \
    rm -rf /var/lib/apt/lists/*
COPY run.sh /client.sh
ENTRYPOINT ["bash", "/client.sh"]
