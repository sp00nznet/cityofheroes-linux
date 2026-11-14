# Notice

The MIT licence in [LICENSE](LICENSE) covers what is ours in this repository:
the Dockerfiles, the scripts, the binary patchers and the documentation. It
does not cover the game or the server.

*City of Heroes* is © Cryptic Studios / NCSoft. The Ouroboros server and
client builds are the Ouroboros project's. None of their executables, data,
piggs or SQL schemas are in this repository; you point `COH_DIR` at your own
Ouroboros install and the containers mount it.

- The patchers (`patch.sh`, `patch_odbc.py`, `patch_idle.py`) change copies
  of the server executables inside the container at start-up. Nothing patched
  is written back to your install or into this repository.
- `winodbc/` holds Windows' own `odbc32.dll` and `odbcint.dll`, copied from
  your Windows machine. They are Microsoft's and are not redistributable, so
  they are mounted, never committed or built into an image.
- Microsoft SQL Server and the Microsoft ODBC Driver 17 are used under
  Microsoft's terms (`ACCEPT_EULA=Y` in `docker-compose.yml`; the driver MSI
  comes from the Ouroboros install's `Setup/SQLInstall`).

*City of Heroes* is a trademark of NCSoft. This project is not affiliated
with or endorsed by NCSoft, Cryptic Studios, Homecoming or the Ouroboros
project. Its interoperability patches were developed by examining the
behaviour of the user's own executables. Running it accepts Microsoft's SQL
Server and ODBC Driver licence terms (`ACCEPT_EULA=Y`,
`IACCEPTMSODBCSQLLICENSETERMS=YES`). No images or binaries are published;
build them yourself. We'll take this down on request from a rights holder.
