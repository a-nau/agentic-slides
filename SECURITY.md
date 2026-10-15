# Security

Please report vulnerabilities privately via GitHub: **Security → Report a
vulnerability** on this repository. Don't open a public issue for them.

## Threat model in short

agentic-slides is a local authoring tool for decks you write or review. Its
deck server (decks, plus the comments/export/edit API on a second port) can
change files in your checkout and renders whatever a deck says, so **whoever
can use its API can edit decks and, through an edited deck, read any file your
user can read and run programs already on disk as Quarto/pandoc filters: treat
API access as code execution as your user** (Quarto/pandoc pull includes,
images, and filters into the rendered page and its exports). What limits who that is:

- **Token login, on by default.** Every page and API request (except the
  `/healthz` probe and CORS preflights, which return no data) needs the token in
  `.quarto/server-token` (owner-only file), sent as a cookie (set by the login
  URL `scripts/start.sh` prints) or an `X-Deck-Token` header.
- It listens on `127.0.0.1` by default; on that bind every request's Host header
  must be loopback too, which blocks DNS rebinding.
- Browser requests with an Origin must come from the server's own pages: same
  hostname, `http`, the deck or API port.
- Quarto renders with `--no-execute`: code chunks never run.

What it doesn't protect against:

- **Other servers on the same hostname.** Browsers send a host's cookies to
  every port, so any other web server you open on that hostname (e.g. another
  `localhost:<port>` app, or another service on a shared workstation) receives
  the login cookie. Use the server only on hostnames whose other services you
  trust.
- **The network, in cleartext.** The server speaks plain HTTP: with
  `SLIDES_HOST=0.0.0.0`, anyone who can watch the traffic sees the token. Use
  it on a trusted network (e.g. a VPN), or keep the default bind and reach it
  through an SSH tunnel (`ssh -L 8093:localhost:8093 -L 8094:localhost:8094 host`).
- **Anyone with the token or login URL** has full access. `scripts/start.sh`
  prints the URL, so it also ends up in terminal and agent logs and in your
  browser history. Treat it like a password; delete `.quarto/server-token` and
  restart to rotate it.
- **Shared machines.** If another user already holds the deck or API port, your
  server can't start, but the login URL `scripts/start.sh` prints would hand the
  token to theirs. On a shared machine, pick unused ports and check that the
  server log says it is serving before you open the URL.
- **`SLIDES_AUTH=off`** removes the login. Then any local user, any page on the
  same hostname, and (with `SLIDES_HOST=0.0.0.0`) anyone on the network can edit
  decks and read your files that way; any website can read and add slide
  comments (they accept `Origin: null`, which exported HTML files send). Use it
  only on a single-user machine bound to `127.0.0.1`. With login off *and*
  `SLIDES_HOST=0.0.0.0`, the Host check is off too, so any website can reach the
  API through DNS rebinding: edit decks and read your files.
- **Decks are trusted content**: they may contain HTML and scripts, and a deck
  file edited on disk is rendered as is. Only open, render, and publish decks
  you wrote or reviewed. Slide comments are untrusted input to the agent that
  addresses them.
