# City of Heroes server on Linux

The Ouroboros **v2i210** (Issue 25) City of Heroes shard, run on Linux, or on
macOS and Windows through Docker Desktop, without a Windows server. The prebuilt
32-bit Windows server executables run under WineHQ 11 in one container, and
Microsoft SQL Server 2022 runs in another. You need your own Ouroboros install.

No server or game files are in this repository ([NOTICE.md](NOTICE.md)).

## Running it

You need Docker (with Compose), an Ouroboros v2i210 install, and two DLLs from
any Windows machine.

1. Copy `C:\Windows\SysWOW64\odbc32.dll` and `odbcint.dll` from Windows into
   `winodbc/`. Wine's own odbc32 can't hand the servers' ANSI ODBC calls to
   Microsoft's Unicode-only driver. The DLLs aren't redistributable, so they
   are mounted, not committed.
2. `cp .env.example .env`, then set `COH_DIR` to the folder holding the
   install's `Server/`, `Setup/` and `Client/`, and pick an `SA_PASSWORD`.
3. `docker compose up -d`. The first run loads the database schemas, then
   starts the shard. Wait for `DbServer Ready` in `docker compose logs -f coh`.
   The first MapServer (Atlas Park) takes a few more minutes to load.
4. Make an account in the admin panel at http://localhost:8080 (user `admin`,
   `PANEL_PASSWORD` from `.env`), which also sets passwords, bans accounts and
   sets GM access levels. Or from the command line:

       python3 addaccount.py NAME PASSWORD | docker compose exec -T db \
         /opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P "$SA_PASSWORD" -d cohauth

5. Point a client at the shard: `-auth <COH_IP> -patchdir ouro -noversioncheck`.
   For play from other machines, set `COH_IP` in `.env` to the host's LAN IP.
   Clients on Linux and macOS are covered by existing guides (Lutris, Wine,
   CrossOver).

## Security

- The game ports (2104-2108, 6950-7100) listen on every interface: anyone who
  can reach the host can reach AuthServer. Firewall them if the host is public.
- MSSQL is not published outside Docker's network. The servers log in as `sa`,
  and `entrypoint.sh` writes that password into the `.cfg` files in your
  `COH_DIR/Server`. Use a password you don't use anywhere else.
- `initdb` refuses to run with an empty or example `SA_PASSWORD`.
- The experimental client's noVNC (6080) is bound to localhost only.

## Resources

The shard idles at about **2.3 GB and half a core**, and MSSQL at about
1.3 GB. Each extra zone that's running adds about 1 GB. An x86-64 machine is
needed; Apple Silicon runs the images through Rosetta (untested).

## Settings (`.env`)

| Variable | Default | |
|---|---|---|
| `COH_DIR` | | Ouroboros install folder |
| `SA_PASSWORD` | | MSSQL sa password |
| `COH_IP` | `127.0.0.1` | Address advertised to clients |
| `MSSQL_MEMORY_LIMIT_MB` | `8192` | MSSQL memory cap. Under ~4 GB its plan cache thrashes once ~10 players are on (DBServer saves are 30 KB batches) |
| `SERVERMONITOR` | `0` | `1` runs the GUI ServerMonitor (costs CPU) |
| `PANEL_PASSWORD` | | Admin panel login (user `admin`); panel won't start without it |
| `PANEL_PORT` | `8080` | Admin panel port (localhost only) |
| `BOTS` | `5` | Bot players to run with `--profile bots` |
| `SCOUT_ZONES` | `1 5 6 71 72` | Zones booted before the bots log in |
| `BOT_MODES` | `+FIGHT +MOVE +CHAT +AUTOREZ` | TestClient behaviours for the bots |
| `PIN_HOSTNAME` | `1` | Map the container's hostname to `COH_IP` (see below) |

## Bots

`docker compose --profile bots up -d` starts `BOTS` bot players. They use the `TestClient.exe` that ships
in the Ouroboros install: each one logs in as `botN`, rolls a random archetype the first time, and
fights in its zone. Measured with 5: ~220 MB RAM and ~7% of a core per bot, plus the MapServer load
of the fights. A bot whose first zone was still booting is restarted a minute later.

Zones only boot when someone enters them (~1 min each under Wine), so before the bots log in a
`scout` account visits each zone in `SCOUT_ZONES` (maps.db ids, default Atlas Park, Kings Row,
Steel Canyon, Mercy Island, Port Oakes) to start it. Set `SCOUT_ZONES=` to skip that step.
Restart just the bots with `docker compose --profile bots up -d --no-deps bots`; without `--no-deps`
compose may recreate the shard too.

Measured with 20 bots (14 heroes in Atlas Park, 7 villains in Mercy Island): the bots container
used 4.3 GB and under half a core; the shard 11.5 GB (each running zone is ~1.9 GB) and about a
core. Each new bot gets its hero name and side on its second login.


## Add-ons

[docs/addons.md](docs/addons.md) covers the built-in admin panel, the
community CityVault player site (running it next to the shard), CoHDBTools,
how to install data mods such as Sophie's Freeform Character Creation, and
running your own build of the Ouroboros source.

## How it works

```
  ┌──────────────┐
  │  CoH client  │   Windows, or Linux/macOS under Wine
  │ -auth COH_IP │
  └──────┬───────┘
         │ 2104-2108 (auth, db)  ·  6950-7100 tcp+udp (maps)
┌────────▼───────────────────────────────────────────────────────┐
│ coh container   debian trixie · WineHQ 11 · hostname cohshard  │
│                                                                │
│   AuthServer ─────────┐                                        │
│   DBServer ◀──────────┼───────── Launcher                      │
│      ▲                │             │ spawns                   │
│      │       ┌────────┴─────────────▼──────────────────────┐   │
│      │       │ MapServer (Atlas Park, …)   QueueServer     │   │
│      │       │ ChatServer  AccountServer   TurnstileServer │   │
│      │       │ StatServer  RaidServer      ArenaServer     │   │
│      │       │ MissionServer  AuctionServer                │   │
│      │       └─────────────────────────────────────────────┘   │
│      │ ODBC: native odbc32 (winodbc/) ─▶ MS ODBC Driver 17     │
└──────┼─────────────────────────────────────────────────────────┘
       │ TDS :1433
┌──────▼───────────────────┐      ┌──────────────────────────────┐
│ db container             │      │ your Ouroboros install       │
│ MSSQL 2022 (capped)      │      │ COH_DIR/Server  ─▶ /coh/...  │
│ cohauth cohacc cohauc    │      │ piggs, data, etc, logs       │
│ cohchat · volume: mssql  │      │ (mounted, never modified)    │
└──────────────────────────┘      └──────────────────────────────┘
```

Start-up, in `entrypoint.sh`:

```
 COH_DIR/Server/*.exe          /run/coh/*.exe (native dir, runs from here)
 ┌───────────────┐   copy   ┌───────────────┐
 │ original EXEs │─────────▶│ runtime copy  │──┐
 └───────────────┘          └───────────────┘  │
        ┌──────────────────────────────────────┘
        ▼
 ┌─────────────┐   ┌───────────────┐   ┌───────────────┐   ┌─────────────────┐
 │  patch.sh   │──▶│ patch_odbc.py │──▶│ patch_idle.py │──▶│ wine reg: 4x6   │
 │ Auth: drop  │   │ ODBC32 …A     │   │ IOCP 1→20 ms  │   │ console font    │
 │ conn pool   │   │ ordinals →    │   │ Sleep 1→10 ms │   │ (560→100 MB per │
 │ call        │   │ plain ANSI    │   │ _kbhit → no-op│   │  console)       │
 └─────────────┘   └───────────────┘   └───────────────┘   └────────┬────────┘
        ┌───────────────────────────────────────────────────────────┘
        ▼
 xvfb-run wine AuthServer ─(5s)─▶ DBServer ─(5s)─▶ Launcher ─▶ the rest
```

Idle, Atlas Park loaded, nobody on:

```
            before                          after
 RAM   coh  ██████████████████████ 6.5 GB   ███████▋              2.3 GB
       db   █████████████████████▏ 6.3 GB   ████▍                 1.3 GB
 CPU   coh  ███████████████████▏   1.9 cores █████                0.5 cores
```

`entrypoint.sh` prepares the shard and starts AuthServer, DBServer and
Launcher; Launcher starts the rest. Each fix below is applied to copies of the
executables made in `/run/coh` at start-up; your install is never modified.

- **Copies, not the mount.** Wine maps PE images as zeros from Docker
  Desktop's Windows-drive bind mounts, so the EXEs and DLLs run from a
  native directory with the data folders symlinked back.
- **ODBC.** The servers talk to MSSQL through Microsoft's ODBC Driver 17,
  installed into the Wine prefix from the install's own MSI, with native
  Windows `odbc32`. FreeTDS misreports `nvarchar(max)` and Debian's Wine 8/10
  lacked or stubbed ODBC calls, hence WineHQ 11.
  - `patch.sh` removes AuthServer's `SQLSetEnvAttr(NULL, CONNECTION_POOLING)`,
    which crashes in Wine.
  - `patch_odbc.py` remaps ODBC32's `…A` ordinal imports to the plain ANSI ones.
- **Hostname.** Launcher passes `-db <hostname>` to MapServers, and a name
  starting with a digit is parsed as an IP, so the container is `cohshard`.
  MapServers advertise `gethostbyname(hostname)` to clients, so it is pinned
  to `COH_IP` in `/etc/hosts`.
- **Memory.** Every server sets a 9999-line console, and Wine's conhost backs
  it with a bitmap of the whole buffer: about 560 MB each at the default font.
  A 4x6 console font brings that to about 100 MB (1x1 hangs the servers).
  MSSQL is capped by `MSSQL_MEMORY_LIMIT_MB`.
- **CPU** (`patch_idle.py`). The servers' main loops wake about 500 times a
  second (a 1 ms network wait, `Sleep(1)`, a `_kbhit()` hotkey check). That's cheap
  on Windows, but under Wine each wake is a wineserver round-trip, about two
  cores at idle. The patch:
  - raises the network wait to `IDLE_MS` (20); it still returns at once on I/O
  - raises `Sleep(1)` to `SLEEP_MS` (10), in back-end servers only, so
    MapServer's game tick is untouched
  - makes the hotkey poll a no-op
  - Patch sites are found by pattern, not fixed offsets.

## Status

Working: the full shard (Auth, DB, Queue, Chat, Account, Turnstile, Stat, Raid,
Mission, Arena, Auction, MapServers). A Windows client logged in, created a
character and entered Atlas Park.

Untested: LAN play from another machine, macOS hosts, a native Linux host
(only Docker Desktop on Windows so far).

Experimental: `docker compose --profile client up client` runs the Windows
client under Wine with noVNC on port 6080; it renders black under llvmpipe.
