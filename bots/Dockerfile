# Bot director: TestClient.exe swarm on the shard image (same Wine prefix). Build context is the repo root.
FROM coh-server
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-pip x11-apps netpbm && \
    pip install --no-cache-dir --break-system-packages pymssql==2.3.7 && rm -rf /var/lib/apt/lists/*
COPY addaccount.py bots/director.py bots/run.sh /bots/
RUN sed -i 's/\r$//' /bots/*
ENTRYPOINT ["bash", "/bots/run.sh"]
