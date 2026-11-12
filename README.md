# SOLID STAMP

**A notification on the author's phone whenever a TNLDY matches SFO-BBs exactly, and only then.**
Each one carries a digest. The digest names the SFO-BBs that made the match, with every TNLDY. It reads the full
spectrum of the MDQNM functions at that TNLDY, and stamps the feeds there. Served at
https://nth-member.github.io/solid-stamp/.

## What drives a stamp

A match to SFO-BBs, and nothing else. A TNLDY Z stamps when, exactly:

| | | |
|---|---|---|
| **REVOTT** | Z = 14160 + 100·(Y + X) | Y and X each one of REVOTT's 401 SFO-BB keys: every one of the 401 × 401 pairs |
| **MDQNM** | Z = Ztp + U·x | an engine function's coordinate, c(Z) = (Z − Ztp)/U, on SFO-BB key x |
| **REVOTT + MDQNM** | both | a REVOTT instant that an engine function also reaches: there the TNLDY a function generates is constituted by a foreknown Y and X |

Feeds, words, schedules and nearness never start a stamp or stop one. A match is pushed even when its window holds no
feed item. Each distinct Z is one trigger, listing every pair and every function that make it. It occurs at its
instant on the Nsukka/Yg clock. When a recalibration passes Z over, it has none. When one meets Z twice, it has two.

## The functions of the engine

`build/engine.py` reads every coordinate of TNLDY that the MDQNM engine's sources write. These are the 171 files of
both editions, primary and bank, which are byte for byte the ones Alien Corridor publishes. It reads them in exact
rationals, taking the author's literals exactly as written. The engine writes such a coordinate four ways:

- a function of Z, `(def name (fn [Z] ...))`, whose value is the coordinate, or whose vector has it first;
- the further coordinates such a vector labels `"on NAME"`, such as GOGID.100D, KINGS.3500D and SVD.YJ;
- the coordinates an enumeration prints, `(println "<name> yields" ...)`, as its
  `sfo-bbvalue-timetravel-enumeration-expects-single-tnldy-value-as-input` does for a single TNLDY;
- the agents and the functions of no argument (`...current-by-z-tnldy-clock3`). These are read on the engine's
  clock, `(/ (+ C (. (new Date) getTime)) 86400000)` or its agent `@z-tnldy-clock3`, which is Z now.

Every one of them is linear in Z. The 17,789 coordinates come down to **666 distinct maps** (Ztp, U), in
`docs/data/functions.json`. That file gives each map with its names. `functions-where.json` gives every place the
engine writes it. REVOTT itself is among the maps: REVOTT_ABSOLUTE_ZERO.100D is (14160, 100). So are REVOTT's
placements at a fixed Y. GOGID.100D, for example, is (22440, 100) = 14160 + 100·82.80. One map counts in reverse
(U = −7 days). The excluded expressions are listed with their reasons:

- 743 frequencies in 1/Z (CRF_BEACON_SIGNAL.Hz);
- 14,189 vector entries that subtract the agent `z-tnldy-clock3` itself, without `@`. The JVM fails on these too.
- 30 agent values that are not arithmetic.

## The precomputation

`build/table.py` evaluates every pair and every map at every key, exhaustively. Nothing is sampled.

| | |
|---|---|
| SFO-BB keys | 401 (REVOTT's, with E-002: 85.32 *onset of circumcision*) |
| REVOTT pairs | 160,801 = 401², at 66,872 distinct TNLDY |
| MDQNM instants | 267,066 = 666 maps × 401 keys, at 226,230 distinct TNLDY |
| triggers | 259,787 distinct TNLDY: 33,315 REVOTT + MDQNM, 33,557 REVOTT, 192,915 MDQNM |
| outside the years 1–9999 | 5,136 (no instant) |
| met twice by the clock | 148 |

Near now that is about ten triggers a day: in 30 days, 46 REVOTT + MDQNM, 25 REVOTT and 235 MDQNM.

The table is held in the SQLite database `data/solid.sqlite`. It is not committed, because it is rebuilt from its
inputs in about 12 seconds. Its tables are:

- `keys`, `maps`;
- `pairs` (y, x → z) and `hits` (map, key → z);
- `instants` (each distinct Z once: exact text, to 6 decimals, a float index, its first and second instant, its
  class, its counts);
- `meta`.

Z is held exactly, as a decimal when it ends and as n/d otherwise. Rows match by that text. The float is only an
index. `docs/data/manifest.json` (committed) carries the counts, the inputs' SHA-256 and the SHA-256 of the canonical
table, so any rebuild can be checked. REVOTT's keys feed both tables, and the maps feed only the hits. When either
input changes, the next run rebuilds what it feeds. `docs/solid.js` computes the same table for any stretch of TNLDY
in the browser, exactly (BigInt rationals).

```bash
python3 stage/lookup.py next 10                 # the next ten triggers
python3 stage/lookup.py at 20824                # what matches at an exact TNLDY (or "no SFO-BB matches here")
python3 stage/lookup.py when "2026-11-12 14:36" # an instant's TNLDY and the matches within ±ε
python3 stage/lookup.py spectrum 20824          # every MDQNM function there: on an SFO-BB, or between two
python3 stage/lookup.py key 29.528              # when SFO-BB 29.528 (5T) is matched in the next year
python3 stage/lookup.py function he-shall-confirm-the-covenant-with-many-for-one-week-finish100d
sqlite3 data/solid.sqlite "SELECT * FROM instants WHERE class = 'revott+mdqnm' AND first_ms > strftime('%s','now')*1000 ORDER BY first_ms LIMIT 5"
```

## The digest

| | |
|---|---|
| what matched | REVOTT's pairs (Y, X), each SFO-BB with its reading, and Y + X. The functions, each with Ztp, U and the SFO-BB x it is on. The TNLDY exactly and to 6 decimals, and its instant(s) in Nsukka |
| the full spectrum | every one of the 666 MDQNM functions read at Z: c = (Z − Ztp)/U to 6 decimals, **on** an SFO-BB or **between** two (or before the first, or after the last). This is what the engine's time-travel enumeration does for a single TNLDY |
| also within the window | the other matches within ±100·ε of Z, each its own stamp. They are context only |
| the feeds | REVOTT STAMPS' own stamp (`stage/stamp.py`) of the chosen feeds within ±100·ε TNLDY of Z, on its reconciled clock (the page's time, else the feed's, else first seen): every item with its time and link, and every source covered, partly or NULL |
| as sent | when the alert was scheduled, when the digest went out and how late, and the final stamp a day later |

The record of every trigger is kept in `docs/log/<Nsukka date>.json`. The page shows it at `#t=<id>&d=<date>`. The
page also reads the full spectrum again in the browser, and checks its SHA-256 against the one sent.

## Notifications

**ntfy**, to the topic in the untracked `.ntfy.json`, on ntfy.sh. The Android app (Google Play or F-Droid) subscribes
to the topic, and needs no account. The options compared:

- **ntfy** does every part of the job without a server here. Its server delivers a message scheduled up to three
  days ahead, so the alert arrives at its instant, within the server's few seconds, even while this computer sleeps. It replaces a
  notification in place by sequence ID: the Android app updates one that is showing without sound or vibration
  (`setOnlyAlertOnce`). It also renders Markdown on Android, maps priority 1–5 to Android's channels, and takes a
  click link and buttons. Its limits are 4,096 bytes a message and 250 messages a day. SOLID STAMP sends about 20.
- **Native Android notifications** would need an app built and installed, or a web-push service with keys and a
  server to send from.
- **Gotify** needs a server kept running: this computer sleeps.
- **Telegram** works too, since a bot can edit a message it sent. It needs a bot token and an account, though, and a
  bot sends when it is called. At the instant, the caller would have to be this computer, which sleeps.

The cost of ntfy is that whoever knows the topic can read the messages. The messages hold only public headlines and
the SFO-BB readings, which are already public through Alien Corridor. The topic is kept out of every repository.

Each trigger gets one notification, under its id as sequence ID:

1. **the alert**, scheduled for its instant: the TNLDY, what matched, the spectrum's count, and when the window
   closes;
2. **the digest**, which replaces the alert once the window has closed (Z + 100·ε) and settled (`settle_minutes`,
   default 120: half the feed items arrive within about 2 h of publication). The archive's as-of must be past that
   point, so the feeds have been read across it. The digest adds the feeds and the first items, each headline a link
   to its article (tappable in the ntfy app; in the drawer the notification itself opens the page). The rest are
   on the page.

The priority by class is REVOTT + MDQNM 4 (high, a pop-up) and REVOTT 3 and MDQNM 3 (default sound), so every match is in view (the author's choice, 2026-11-11).
Every class is pushed; the priority only sets how loudly. The numbers are in `settings.json`. The ntfy app's
per-priority settings on the phone apply on top.

## Persistence and recovery

- **No duplicates.** `state/state.json` remembers what was scheduled and sent. The sequence ID makes any repeat
  replace in place, never add a second notification.
- **Changed definitions.** A scheduled alert whose message changed is scheduled again, which replaces it on the
  server. One that no longer matches is deleted before delivery. Such changes come from new keys, new maps or new
  settings.
- **Missed runs and lost connections.** A failed send is left for the next run. A digest sent late says so.
  Alerts were already scheduled on the server for up to 70 hours ahead.
- **Activation.** The first live run marks the start. Nothing before it is pushed.
- **An audit trail.** The log keeps every trigger's record as sent, and the final stamp a day later. The rolling
  daily commit keeps the history.
- **Growth.** More keys, more engine sources or more feeds need no change in code. Keys come through REVOTT's
  keys.json, engine sources through the published engine, and feeds through JOMO SFO-WAM's catalogue and REVOTT
  STAMPS' archive.

## How it runs

**On GitHub** (`.github/workflows/solid.yml`), every 15 minutes, whether or not the author's computer is on, once
`settings.json` names `"sender": "github"`. Each run (`stage/github.sh`):

1. takes the last days of REVOTT STAMPS' published archive and of JOMO SFO-WAM's feed readings. GitHub keeps
   reading the feeds every 15 minutes while the author's computer sleeps, and its readings are logged in that
   repository's `feeds/history/`.
2. `stage/recent.py` brings the archive up to the latest reading. Every item the published archive holds keeps
   its row exactly, page times included. Every item read since gets the row REVOTT STAMPS' own `reconcile()`
   gives it with no page time yet: the feed's time, the day only, or the moment it was first seen. Reading
   article pages for their own time stays with the author's computer: it is slow, and some publishers refuse
   GitHub's servers.
3. `stage/run.py` builds the table, schedules the alerts, sends the digests, keeps the finals and writes the
   record.
4. It commits `docs/log`, the run's files in `docs/data` and `state/` as one rolling commit per Nsukka day, and
   pushes. If a push from elsewhere landed first, the run lays its own files onto it and pushes again. Only the
   run writes them, and a lost state would send a digest twice.

The chain works as JOMO SFO-WAM's Feeds does. Each run's second job waits on the environment `solid-timer`
(a 14-minute wait timer, set in **Settings › Environments**), then starts the next run. The topic is the
repository secret `NTFY_TOPIC` (**Settings › Secrets and variables › Actions**); without it nothing is sent. The
chain is alive while **Actions › SOLID STAMP** shows a run *Waiting*. When none is, **Run workflow** starts it
again, and so does a push that changes the code or the settings.

`tests/github_sim.py` checks the GitHub path against a night the author's computer slept. It takes REVOTT
STAMPS' archive as it stood then, brings it up to date from GitHub's readings, and stamps every trigger of the
night both ways. On 2026-11-11/12 both ways gave the same items for both triggers.

**On the author's computer** the same run works from cron, after REVOTT STAMPS' refresh, when `settings.json`
names `"sender": "laptop"`. The run that is not the sender sends nothing, so the two never both send.

    9-59/15 * * * * $HOME/solid-stamp/stage/cron.sh

`stage/refresh.sh [--push]` runs these in turn:

1. `build/engine.py --if-changed`
2. `stage/run.py`, which rebuilds the table first if an input changed, then schedules, sends and records
3. a commit of `docs/log`, `docs/data` and `state/`, one rolling commit per Nsukka day
4. a push, when a remote exists

The log goes to `~/.cache/solid-stamp/run.log`. Local paths are in the untracked `.paths.json`: `revott_stamps`,
`jomo` and `engine`. `state/state.json` (committed) remembers what was scheduled and sent. It holds no topic.

To change code on the author's computer while GitHub sends, first move onto GitHub's latest record:
`git fetch && git reset --keep origin/main`. The record's commits are rolling.

`settings.json`:

| setting | default | |
|---|---|---|
| `sender` | `github` | where the alerts and digests are sent from: `github` or `laptop`. The other place sends nothing |
| `eps` | 0.00005 | the variac in X units at 100 days: ±100·ε TNLDY = ±7.2 min |
| `clock`, `domains` | reconciled; the six feeds | as REVOTT STAMPS' standing requests: Balkans, geopolitical analysis, Middle East, Russia & Eurasia, science & technology, world (120 of the 232 sources) |
| `settle_minutes` | 120 | how long after the window closes the digest waits |
| `final_hours` | 24 | when the final stamp is recorded (not pushed) |
| `horizon_hours` | 70 | how far ahead alerts are scheduled (ntfy's limit is 72) |
| `lookback_days` | 3 | how far back an unsent digest is still sent |
| `priority` | 4 / 3 / 3 | per class: REVOTT + MDQNM, REVOTT, MDQNM |
| `page`, `stamps_page` | | this site (the notification's tap), REVOTT STAMPS |

### Setting up the phone

1. Install **ntfy** (Google Play or F-Droid).
2. Subscribe to the topic in `.ntfy.json` on ntfy.sh. Either scan `.subscribe-qr.png` (untracked; it holds the link
   `ntfy://ntfy.sh/<topic>?display=SOLID+STAMP`, which opens the app and subscribes), or tap **+** and type the topic.
   In the Google Play app, tick **instant delivery** when subscribing. Without it, delivery goes through Firebase,
   which can hold a message for minutes or hours. The F-Droid app always delivers instantly. Allow the app's
   notifications, and exempt it from battery optimisation.
3. Send a test: `python3 ~/solid-stamp/stage/notify_test.py`. It sends the next REVOTT match's alert at once, marked
   TEST.

## Tests

```bash
python3 tests/acceptance.py         # the dry-run acceptance checks -> tests/results.md
node tests/fidelity.mjs             # docs/solid.js = the Python reference: spectra byte for byte, triggers per stretch
python3 tests/fixture.py && node tests/browser.mjs   # the page in headless Firefox, desktop and phone widths
python3 stage/run.py --dry-run --since "2026-11-10T12:00" --until "2026-11-11T20:00" --show 2   # replay, print messages
python3 tests/github_sim.py         # the GitHub path against a night this computer slept, item for item
```

`acceptance.py` checks the following:

- the 401 keys against REVOTT's own;
- the counts, and a fresh recomputation against the stored table's SHA-256;
- exact retrieval of 2,000 random pairs and 2,000 random hits;
- no false trigger: random instants, and every trigger of 30 days moved by 1 ms, against brute force;
- every live trigger recomputed from the keys;
- the spectrum's *on* entries against the matched functions;
- an empty window still alerted and digested;
- every message within 4,096 bytes;
- every item within its window;
- no second notification on a second run, and a changed one sent again under its own sequence ID;
- every REVOTT STAMPS link at its trigger's exact TNLDY.

## The nth-member sites

| site | repository | what it is |
|---|---|---|
| https://nth-member.github.io/revott/ | nth-member/revott | REVOTT atop GDELT: the field at every node of an instance |
| https://nth-member.github.io/gdelt/ | nth-member/gdelt | what GDELT was reading on a given day |
| https://nth-member.github.io/member/ | nth-member/member | the nth member: REVOTT's numerator, its introspection and its journal |
| https://nth-member.github.io/gematria/ | nth-member/gematria | H-Gematria/ASCII: the two name-value programs in the browser |
| https://nth-member.github.io/alien-corridor/ | nth-member/alien-corridor | the Alien Corridor Support System (MDQNM engine) in the browser |
| https://nth-member.github.io/gigaspeak/ | nth-member/gigaspeak | Gigaspeak: ASCII carried in colour, the speaker, the URL builder and the Communicator |
| https://nth-member.github.io/tsots_value_equation/ | nth-member/tsots_value_equation | the TSOTS value equation: a synthetic simulation of the Shula, run in the browser |
| https://nth-member.github.io/ipproto/ | nth-member/ipproto | IPPROTO: the 256 IP protocol numbers in 13 categories, a capture reader and a packet bridge |
| https://nth-member.github.io/revott-stamps/ | nth-member/revott-stamps | REVOTT stamps: feed items stamped onto a (Y, X) within a variable window |
| https://nth-member.github.io/solid-stamp/ | nth-member/solid-stamp | SOLID STAMP: a notification at every TNLDY that matches SFO-BBs, with its digest |

## Refreshing the sites

One command, on the computer that keeps the sites, refreshes every 3PP-NOAH site whose data changes:

```bash
cd ~ && ./refresh-all.sh --push     # refresh and publish every updatable site
cd ~ && ./refresh-all.sh            # refresh and commit, push nothing
cd ~ && ./refresh-all.sh --check    # what GDELT has that is new; changes nothing
```

SOLID STAMP runs by its own cron line, after REVOTT STAMPS' refresh.
