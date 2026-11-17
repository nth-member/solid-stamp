# SOLID STAMP — acceptance checks

Run 2026-11-17 07:09 Nsukka · table 98ba1149f5d4e664 · 14/14 pass

| check | result | note |
|---|---|---|
| 539 SFO-BBs: distinct, ascending, the same values as REVOTT's own keys, 85.32, -19.60 and 24.31 among them, 241.20 blotted out | PASS | 539 keys, -147.6 .. 212.4 |
| the engine's maps: every coordinate linear in Z, exact; REVOTT itself and GOG_ID among them | PASS | 666 distinct maps from 17789 coordinates; excluded {'division by Z': 743, 'the symbol z-tnldy-clock3': 14189, 'not an arithmetic form': 30} |
| the precomputation is exhaustive: 539 × 539 pairs and every map at every key, counts as the manifest says | PASS | 290521 pairs, 358974 hits, 355557 distinct TNLDY |
| a fresh recomputation reproduces the stored table exactly (SHA-256 of the canonical table) | PASS | 98ba1149f5d4e664 |
| stored combinations are retrieved exactly: 2,000 random pairs and 2,000 random (map, key) hits | PASS |  |
| non-matching TNLDY values never trigger: random instants, and every trigger of 30 days moved by 1 ms, by brute force | PASS | 500 random instants (0 matches) and 948 moved triggers: the table agrees with brute force on all |
| every live trigger is an exact match: the next 30 days, each pair and hit recomputed from the keys | PASS | 474 triggers in 30 days: {'revott+mdqnm': 76, 'revott': 48, 'mdqnm': 350} |
| the spectrum's 'on' entries are exactly the trigger's matched functions (200 triggers) | PASS |  |
| the driver is the match alone: a trigger whose window holds no item is still alerted and digested | PASS | sscd6e48f65ecb23 |
| every message fits ntfy's 4,096 bytes, and every digest goes at digest_min_priority or more | PASS | largest 3804 bytes |
| every stamped item lies within ±100·ε TNLDY of its trigger, on the reconciled clock | PASS | 845 items checked |
| duplicates: a second run with nothing new sends nothing; a changed message replaces by the same sequence ID | PASS | first run 46 scheduled, second run 0, a changed one re-sent under its own sequence ID |
| the morning re-send: a digest first sent in the night is sent again once, from 07:00, under its sequence ID | PASS | the digest of 20827.385233 sent again once at 07:10, not again after |
| REVOTT STAMPS links open the same TNLDY: Y + X of the link's request gives the trigger's Z exactly | PASS | 139 links checked |
