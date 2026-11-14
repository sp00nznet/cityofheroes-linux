# Add-ons: control panels, data mods and source builds

Community tools for Ouroboros shards, and how each fits a server running in
these containers. None of them are in this repository: get them from their
authors, and check their licences.

```
                    ┌──────────────────── docker network ─────────────────────┐
 browser ──▶ panel  │  panel (ours) ──┐                                       │
 (localhost:8080)   │                 ├──▶ db: MSSQL  cohauth  cohdb  …       │
 players ──▶ CityVault (optional) ────┘          ▲                            │
                    │                            │ ODBC                       │
                    │                   coh: the shard under Wine             │
                    │                     Server/data/bin ◀── binned mods     │
                    └─────────────────────────────────────────────────────────┘
```

## The built-in panel (`panel/`)

The panel is a small admin page that ships with this repo. It's for the shard's
admin, not for players, and it runs by default.

- **Accounts:** create one, set its password (same hash as `addaccount.py` and
  CoHDBTools), ban or unban it.
- **Characters:** list them per account, with level, class, origin and when
  last online. Set a character's access level (GM, admin); this takes effect
  the next time it logs in.
- **Status:** AuthServer, DBServer and MSSQL up or down, and how many players
  are online.

Set `PANEL_PASSWORD` in `.env`, then open http://localhost:8080 and log in as
user `admin`. It listens on localhost only. To reach it from elsewhere, put it
behind a reverse proxy with TLS rather than publishing the port. It logs in to
MSSQL as `sa`.

## CityVault (player website)

[CityVault](https://github.com/CaitlynMainer/CityVault) by Caitlyn Mainer
(MIT) is a Node.js site for players. It offers:
- sign-up, email verification and password reset
- character profiles
- launcher manifest generation
- an admin dashboard, with multi-server support

It's meant to face the internet. It gets its own HTTPS certificate for your
domain on the first request, so it needs a real domain pointed at the host and
ports 80/443 open.

Its database is the same MSSQL. To run it next to the shard, add a
`docker-compose.override.yml` beside `docker-compose.yml`:

```yaml
services:
  cityvault:
    image: node:22
    working_dir: /app
    # msnodesqlv8 is CityVault's Windows-only LocalDB driver and won't build on Linux; with host `db`
    # it uses the pure-JS tedious driver, so drop it before installing.
    command: sh -c "npm pkg delete dependencies.msnodesqlv8 && npm install --no-audit --no-fund && npm start"
    volumes: [ "${CITYVAULT_DIR}:/app" ]   # your CityVault checkout
    depends_on: [ db ]
    ports: [ "80:80", "443:443" ]
```

Then set `CITYVAULT_DIR` in `.env`. The first start runs an interactive setup wizard, so run it in a
terminal once with `docker compose run --rm --service-ports cityvault`, and afterwards use
`docker compose up -d cityvault`. (Tested this far on Linux: dependencies install and the wizard
starts; the rest is untested.) The wizard asks for the SQL server: use host `db`, port 1433, user `sa`
and your `SA_PASSWORD`. A dedicated SQL login is better if the site is public.
For a downloadable client, follow its README's "Hosting Game Files" section.
Launch parameters for this shard are `-patchdir ouro -auth <COH_IP>`.

## CoHDBTools (in the Ouroboros install)

`CoHDBTools10/www` in the Ouroboros install is the PHP admin and sign-up site
from the Windows self-installer (it runs under XAMPP there). Our panel covers
its account tasks. To run it anyway, any PHP image with the `sqlsrv` extension
can serve it against host `db`.

## Data mods (e.g. Sophie's Freeform Character Creation)

Mods like [Sophie's Freeform](https://git.ourodev.com) add or change game data:
recipes, vendors, powers and texts. The server doesn't read those files
directly. It reads compiled `.bin` files from `Server/data/bin`, and those
override the copies inside the piggs.

**Don't bin a mod against the server install on its own.** The install ships
only the compiled bins, not the source data. Binning there would produce, for
example, an `InvRecipe.bin` with only the mod's recipes and none of the
game's.

The workflow:

1. Get the Ouroboros server-data workspace from their GitLab. This is the
   `bin-server` repository the mod readmes refer to, e.g.
   `i2401-bin-server.git\bin\serverdata`.
2. Copy the mod's files to where its readme says. For Sophie's:
   - the `*.recipe` files go in `serverdata/Defs/Invention`
   - `RecipesEndgame.xls.ms` goes in `serverdata/texts/English/Bases`, merged
     by hand if you've changed that file before
3. Bin the workspace. MapServer has a `-createbins` switch for this, and it is
   in the release MapServer.exe too. Run it on Windows the way the workspace
   README says, or under Wine:

       docker compose run --rm --entrypoint bash -v /path/to/workspace:/ws coh \
         -c 'cd /ws/bin && wine /coh/Server/MapServer.exe -createbins'

4. Copy the changed `.bin` files into `COH_DIR/Server/data/bin`. Back up the
   originals first.
5. Refresh the database templates once: stop the shard, then run
   `MapServer.exe -templates` the same way as step 3.
6. Restart: `docker compose restart coh`. If the mod changes what players see
   (texts, new items), clients need the matching bins too. Ship them the way
   the mod's readme says.

The Wine route for steps 3 and 5 is untested. If it fails, bin on Windows
and copy the bins over. Running them doesn't change.

## Building from source ((Co)X develop branch)

The Ouroboros `source` repository's `develop` branch ("Project (Co)X") is the
code behind these server builds, plus later fixes. It builds with **Visual
Studio 2008 on Windows** (see its README). This repo doesn't build it. It
runs whatever server EXEs are in `COH_DIR/Server`.

To run your own build, replace the EXEs in `COH_DIR/Server` with yours and
restart, then check `docker compose logs coh`:

- `patch_odbc.py` and `patch_idle.py` find their sites by pattern, so they
  should work on rebuilt EXEs. A `site(s)` line reading 0 means that fix
  didn't apply.
- `patch.sh` (AuthServer) is offset-based. It checks the bytes first, and on
  a different build it prints `WARN ... unexpected bytes` and leaves the file
  alone. If you see that, a rebuilt AuthServer needs its two
  `SQLSetEnvAttr(NULL, …CONNECTION_POOLING…)` calls removed, or
  connection pooling turned off in your source.
