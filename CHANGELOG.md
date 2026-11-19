# Changelog

All notable changes to this project. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/).

## [Unreleased]

### Added
- The Ouroboros v2i210 shard (Auth, DB, Launcher and everything it starts,
  MapServers included) running under WineHQ 11 in Docker, with MSSQL 2022 in a
  second container. A Windows client logged in, made a character and entered
  Atlas Park.
- `initdb.sh` loads the Ouroboros schemas once; `addaccount.py` makes an
  account with the same password hash as CoHDBTools.
- Wine compatibility patches applied to runtime copies of the EXEs:
  `patch.sh` (AuthServer connection pooling call), `patch_odbc.py` (ODBC32
  ordinal imports).
- `patch_idle.py`: idle shard CPU from ~1.9 cores to ~0.5.
- Memory: 4x6 console font (conhost ~560 MB to ~100 MB each), MSSQL capped
  at `MSSQL_MEMORY_LIMIT_MB`. Idle total ~13 GB to ~3.6 GB.
- `panel/`: admin panel (create accounts, set passwords, ban, character access
  levels, shard status). Python stdlib + pymssql, Basic auth, localhost only.
- `docs/addons.md`: CityVault (runs on Linux once its Windows-only LocalDB
  driver is dropped), CoHDBTools, data mods and binning, source builds.
- Experimental Linux client container (`--profile client`, noVNC); renders
  black under llvmpipe so far.
- `bots/`: bot players (`--profile bots`). A director keeps `BOTS` copies of
  the shipped `TestClient.exe` logged in, names them, sends villain archetypes
  to Mercy Island, and has a scout boot zones first. 20 bots measured.

### Fixed
- Panel-made accounts couldn't log in (password hash stored as UTF-16).
- MSSQL default cap 2 GB → 8 GB: at 2 GB, saves recompiled constantly.
