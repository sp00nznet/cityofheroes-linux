# CoH (Ouroboros i25) server under WineHQ, talking to MSSQL through the MS ODBC driver.
FROM debian:trixie-slim
ARG WINE_BRANCH=stable
RUN dpkg --add-architecture i386 && apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends wget ca-certificates gnupg && \
    mkdir -pm755 /etc/apt/keyrings && wget -qO /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key && \
    wget -qNP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/debian/dists/trixie/winehq-trixie.sources && \
    apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --install-recommends winehq-$WINE_BRANCH && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      unixodbc tdsodbc libodbc2:i386 libodbcinst2:i386 tdsodbc:i386 freetds-bin procps xxd xvfb xauth python3 && \
    rm -rf /var/lib/apt/lists/*
RUN printf '[FreeTDS]\nDriver=/usr/lib/i386-linux-gnu/odbc/libtdsodbc.so\n' > /etc/odbcinst.ini
ENV WINEPREFIX=/wine WINEDEBUG=-all
RUN wineboot -i && wineserver -w
COPY entrypoint.sh patch.sh patch_odbc.py patch_idle.py /
# Windows checkouts add CRLF; bash chokes on it.
RUN sed -i 's/\r$//' /entrypoint.sh /patch.sh /patch_odbc.py /patch_idle.py
WORKDIR /coh/Server
ENTRYPOINT ["bash", "/entrypoint.sh"]
