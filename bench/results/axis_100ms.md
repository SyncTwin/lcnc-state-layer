Trace `axis_100ms`, 1383 ticks, poll period 0.1 s (budget per tick 100000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 15959 | 15979 | 16004 | 16051 | 219 / 237 | 400 / 420 | – | – | 0.0 % | 0.62 % |  |
| json_merge_patch | nlohmann | 6302 | 6509 | 6705 | 7850 | 461 / 482 | 182 / 200 | 53.3 | 50.7 | 0.0 % | 0.64 % |  |
| cbor_full | nlohmann | 13849 | 13856 | 13860 | 13876 | 197 / 214 | 394 / 410 | – | – | 0.0 % | 0.59 % |  |
| cbor_merge_patch | nlohmann | 5387 | 5563 | 5695 | 6616 | 452 / 477 | 164 / 181 | 53.5 | 45.5 | 0.0 % | 0.62 % |  |
| msgpack_full | nlohmann | 13894 | 13899 | 13907 | 13923 | 198 / 216 | 395 / 416 | – | – | 0.0 % | 0.59 % |  |
| msgpack_merge_patch | nlohmann | 5423 | 5601 | 5731 | 6655 | 446 / 468 | 161 / 178 | 52.1 | 45.1 | 0.0 % | 0.61 % |  |
| json_merge_patch_objidx_structs | nlohmann | 744 | 749 | 983 | 1217 | 511 / 548 | 27.9 / 39.8 | 58.6 | 6.6 | 0.0 % | 0.54 % |  |
| json_merge_patch_objidx_all | nlohmann | 508 | 542 | 688 | 1027 | 631 / 655 | 19.6 / 26.0 | 79.0 | 4.7 | 0.0 % | 0.65 % |  |
| fb_full | flatbuffers | 6367 | 6376 | 6384 | 6392 | 6.7 / 7.1 | 3.6 / 3.7 | – | – | 0.0 % | 0.01 % |  |
| fb_delta | flatbuffers | 1998 | 2040 | 2224 | 2536 | 4.0 / 4.5 | 1.9 / 2.0 | 4.0 | – | 0.0 % | 0.01 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 15959 | 15979 | 16004 | 16051 | 210 / 226 | 349 / 363 | – | – | 0.0 % | 0.56 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6367 | 6376 | 6384 | 6392 | 6.9 / 7.5 | 2.5 / 2.6 | – | – | 0.0 % | 0.01 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 15959 | 15979 | 16004 | 16051 | 285 / 344 | 293 / 348 | – | – | 0.0 % | 0.58 % |  |
| json_merge_patch | json | 6302 | 6509 | 6705 | 7850 | 171 / 200 | 109 / 134 | 58.9 | 7.0 | 0.0 % | 0.28 % |  |
| json_full_deflate | json+zlib | 313 | 324 | 374 | 1445 | 408 / 458 | 313 / 344 | – | – | 0.0 % | 0.72 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 199 | 204 | 330 | 436 | 235 / 299 | 124 / 158 | 62.3 | 8.0 | 0.0 % | 0.36 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6477 | 6474 | 6670 | 7815 | 172 / 221 | 109 / 145 | 58.2 | 6.9 | 3.3 % | 0.28 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6477 | 6474 | 6670 | 7815 | 817 / 886 | 115 / 139 | 439 | 7.6 | 3.2 % | 0.93 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 744 | 749 | 983 | 1217 | 377 / 451 | 29.6 / 45.1 | 80.8 | 5.8 | 0.0 % | 0.41 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 508 | 542 | 688 | 1027 | 576 / 656 | 27.9 / 40.1 | 113 | 8.2 | 0.0 % | 0.60 % | all arrays as {index: value} |
| json_full | orjson | 15959 | 15979 | 16004 | 16051 | 41.9 / 45.1 | 86.0 / 94.9 | – | – | 0.0 % | 0.13 % |  |
| json_merge_patch | orjson | 6302 | 6509 | 6705 | 7850 | 66.3 / 74.5 | 29.1 / 34.7 | 50.8 | 5.4 | 0.0 % | 0.10 % |  |
| cbor_full | cbor2 | 16816 | 16820 | 16821 | 16821 | 279 / 312 | 378 / 405 | – | – | 0.0 % | 0.66 % |  |
| cbor_merge_patch | cbor2 | 6189 | 6391 | 6543 | 7552 | 164 / 201 | 136 / 170 | 59.1 | 10.2 | 0.0 % | 0.30 % |  |
| msgpack_full | msgpack | 16861 | 16863 | 16867 | 16867 | 82.1 / 93.9 | 149 / 179 | – | – | 0.0 % | 0.23 % |  |
| msgpack_merge_patch | msgpack | 6226 | 6429 | 6579 | 7591 | 81.4 / 91.5 | 55.1 / 63.9 | 53.9 | 5.3 | 0.0 % | 0.14 % |  |
| fb_full | flatbuffers | 6261 | 6272 | 6280 | 6288 | 2260 / 2479 | 2277 / 2462 | – | – | 0.0 % | 4.54 % |  |
| fb_delta | flatbuffers | 1950 | 1992 | 2176 | 2464 | 984 / 1104 | 1034 / 1153 | 984 | 1034 | 0.0 % | 2.02 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8383 | 8383 | 8387 | 8387 | 846 / 980 | 132 / 159 | – | – | 0.0 % | 0.98 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 156 | 165 | 223 | 356 | 2803 / 3068 | 46.5 / 83.8 | 2170 | 33.4 | 1.7 % | 2.85 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14485 | 14505 | 14532 | 14585 | 59.7 / 63.6 | 67.5 / 70.5 | – | – | 0.0 % | 0.13 % |  |
| json_merge_patch | JSON | 5907 | 6101 | 6286 | 7394 | 106 / 120 | 29.9 / 34.7 | 78.5 | 1.9 | 0.0 % | 0.14 % |  |
| cbor_full | cbor-x | 11058 | 11065 | 11073 | 11105 | 116 / 123 | 188 / 205 | – | – | 0.0 % | 0.30 % |  |
| cbor_merge_patch | cbor-x | 4649 | 4798 | 4915 | 5754 | 131 / 144 | 59.5 / 66.3 | 76.8 | 1.7 | 0.0 % | 0.19 % |  |
| msgpack_full | @msgpack/msgpack | 10984 | 10991 | 11002 | 11034 | 155 / 172 | 140 / 152 | – | – | 0.0 % | 0.30 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4653 | 4803 | 4918 | 5744 | 139 / 151 | 53.8 / 58.3 | 76.8 | 1.8 | 0.0 % | 0.19 % |  |

