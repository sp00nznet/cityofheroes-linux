# Contributing

Issues and pull requests are welcome.

## The one rule

**Nothing from the game, the server or Windows goes in the repository.** No
executables (patched or not), no piggs or data, no SQL schemas or database
dumps, no `odbc32.dll`/`odbcint.dll`. `.gitignore` covers `winodbc/` and
`.env`; check `git status` before you commit anyway.

## Before a pull request

1. `docker compose up -d --build` from a clean `docker compose down`, and wait
   for `DbServer Ready` in `docker compose logs coh`.
2. Log in with a client, create or load a character and enter a zone.
3. A new binary patch says in a comment what it changes, why Wine needs it, and
   finds its site by pattern, not by a hard-coded offset where it can.
