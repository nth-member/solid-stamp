# SOLID STAMP — acceptance checks

Run 2026-11-12 07:45 Nsukka · table f9840de3c6633e21 · 13/13 pass

| check | result | note |
|---|---|---|
| 401 SFO-BBs: distinct, ascending, the same values as REVOTT's own keys, 85.32 among them | PASS | 401 keys, -147.6 .. 212.4 |
| the engine's maps: every coordinate linear in Z, exact; REVOTT itself and GOG_ID among them | PASS | 666 distinct maps from 17789 coordinates; excluded {'division by Z': 743, 'the symbol z-tnldy-clock3': 14189, 'not an arithmetic form': 30} |
| the precomputation is exhaustive: 401 × 401 pairs and every map at every key, counts as the manifest says | PASS | 160801 pairs, 267066 hits, 259787 distinct TNLDY |
| a fresh recomputation reproduces the stored table exactly (SHA-256 of the canonical table) | PASS | f9840de3c6633e21 |
| stored combinations are retrieved exactly: 2,000 random pairs and 2,000 random (map, key) hits | PASS |  |
| non-matching TNLDY values never trigger: random instants, and every trigger of 30 days moved by 1 ms, by brute force | PASS | 500 random instants (0 matches) and 612 moved triggers: the table agrees with brute force on all |
| every live trigger is an exact match: the next 30 days, each pair and hit recomputed from the keys | PASS | 306 triggers in 30 days: {'revott+mdqnm': 46, 'revott': 26, 'mdqnm': 234} |
| the spectrum's 'on' entries are exactly the trigger's matched functions (200 triggers) | PASS |  |
| the driver is the match alone: a trigger whose window holds no item is still alerted and digested | PASS | ss6be71236b29f35 |
| every message fits ntfy's 4,096 bytes: the next 30 days' alerts and the last 3 days' digests | PASS | largest 3498 bytes |
| every stamped item lies within ±100·ε TNLDY of its trigger, on the reconciled clock | PASS | 542 items checked |
| duplicates: a second run with nothing new sends nothing; a changed message replaces by the same sequence ID | PASS | first run 26 scheduled, second run 0, a changed one re-sent under its own sequence ID |
| REVOTT STAMPS links open the same TNLDY: Y + X of the link's request gives the trigger's Z exactly | PASS | 83 links checked |
