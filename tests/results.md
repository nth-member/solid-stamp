# SOLID STAMP — acceptance checks

Run 2026-11-18 20:13 Nsukka · table 0ff75f66d4f74c88 · 14/14 pass

| check | result | note |
|---|---|---|
| 550 SFO-BBs: distinct, ascending, the same values as REVOTT's own keys, 85.32, -19.60, 24.31 and the evens 42.118 .. 81.718 among them, 60.118 beside 60.12, 241.20 blotted out | PASS | 550 keys, -147.6 .. 212.4 |
| the engine's maps: every coordinate linear in Z, exact; REVOTT itself and GOG_ID among them | PASS | 666 distinct maps from 17789 coordinates; excluded {'division by Z': 743, 'the symbol z-tnldy-clock3': 14189, 'not an arithmetic form': 30} |
| the precomputation is exhaustive: 550 × 550 pairs and every map at every key, counts as the manifest says | PASS | 302500 pairs, 366300 hits, 362633 distinct TNLDY |
| a fresh recomputation reproduces the stored table exactly (SHA-256 of the canonical table) | PASS | 0ff75f66d4f74c88 |
| stored combinations are retrieved exactly: 2,000 random pairs and 2,000 random (map, key) hits | PASS |  |
| non-matching TNLDY values never trigger: random instants, and every trigger of 30 days moved by 1 ms, by brute force | PASS | 500 random instants (0 matches) and 970 moved triggers: the table agrees with brute force on all |
| every live trigger is an exact match: the next 30 days, each pair and hit recomputed from the keys | PASS | 485 triggers in 30 days: {'revott+mdqnm': 77, 'revott': 56, 'mdqnm': 352} |
| the spectrum's 'on' entries are exactly the trigger's matched functions (200 triggers) | PASS |  |
| the driver is the match alone: a trigger whose window holds no item is still alerted and digested | PASS | ssd785475d6c34d0 |
| every message fits ntfy's 4,096 bytes and, as Firebase receives it, 3,500; every digest at digest_min_priority+ | PASS | largest 2737 bytes |
| every stamped item lies within ±100·ε TNLDY of its trigger, on the reconciled clock | PASS | 1071 items checked |
| duplicates: a second run with nothing new sends nothing; a changed message replaces by the same sequence ID | PASS | first run 46 scheduled, second run 0, a changed one re-sent under its own sequence ID |
| the morning re-send: a digest first sent in the night is sent again once, from 07:00, under its sequence ID | PASS | the digest of 20828.415930 sent again once at 07:10, not again after |
| REVOTT STAMPS links open the same TNLDY: Y + X of the link's request gives the trigger's Z exactly | PASS | 136 links checked |
