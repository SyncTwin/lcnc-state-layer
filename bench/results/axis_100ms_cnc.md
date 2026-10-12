Trace `axis_100ms`, 1383 ticks, poll period 0.1 s (budget per tick 100000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 15959 | 15979 | 16004 | 16051 | 207 / 210 | 353 / 358 | – | – | 0.0 % | 0.56 % |  |
| json_merge_patch | nlohmann | 6302 | 6509 | 6705 | 7850 | 394 / 399 | 154 / 162 | 43.8 | 39.2 | 0.0 % | 0.55 % |  |
| cbor_full | nlohmann | 13849 | 13856 | 13860 | 13876 | 182 / 183 | 340 / 343 | – | – | 0.0 % | 0.52 % |  |
| cbor_merge_patch | nlohmann | 5387 | 5563 | 5695 | 6616 | 382 / 386 | 138 / 145 | 44.6 | 35.0 | 0.0 % | 0.52 % |  |
| msgpack_full | nlohmann | 13894 | 13899 | 13907 | 13923 | 178 / 180 | 339 / 343 | – | – | 0.0 % | 0.52 % |  |
| msgpack_merge_patch | nlohmann | 5423 | 5601 | 5731 | 6655 | 376 / 380 | 136 / 143 | 42.6 | 34.4 | 0.0 % | 0.51 % |  |
| json_merge_patch_objidx_structs | nlohmann | 744 | 749 | 983 | 1217 | 455 / 477 | 20.4 / 28.9 | 51.5 | 4.8 | 0.0 % | 0.48 % |  |
| json_merge_patch_objidx_all | nlohmann | 508 | 542 | 688 | 1027 | 548 / 564 | 13.5 / 17.9 | 66.2 | 3.0 | 0.0 % | 0.56 % |  |
| fb_full | flatbuffers | 6367 | 6376 | 6384 | 6392 | 5.8 / 6.0 | 3.8 / 3.8 | – | – | 0.0 % | 0.01 % |  |
| fb_delta | flatbuffers | 1998 | 2040 | 2224 | 2536 | 3.1 / 3.3 | 2.0 / 2.0 | 3.1 | – | 0.0 % | 0.01 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 15959 | 15979 | 16004 | 16051 | 200 / 202 | 310 / 313 | – | – | 0.0 % | 0.51 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6367 | 6376 | 6384 | 6392 | 5.7 / 6.0 | 2.5 / 2.6 | – | – | 0.0 % | 0.01 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 15959 | 15979 | 16004 | 16051 | 196 / 203 | 275 / 282 | – | – | 0.0 % | 0.47 % |  |
| json_merge_patch | json | 6302 | 6509 | 6705 | 7850 | 119 / 128 | 102 / 111 | 41.7 | 5.2 | 0.0 % | 0.22 % |  |
| json_full_deflate | json+zlib | 313 | 324 | 374 | 1445 | 283 / 307 | 291 / 297 | – | – | 0.0 % | 0.57 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 199 | 204 | 330 | 436 | 160 / 189 | 110 / 120 | 42.9 | 5.6 | 0.0 % | 0.27 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6477 | 6474 | 6670 | 7815 | 118 / 123 | 103 / 109 | 40.9 | 4.8 | 3.3 % | 0.22 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6477 | 6474 | 6670 | 7815 | 629 / 647 | 107 / 113 | 339 | 5.3 | 3.2 % | 0.74 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 744 | 749 | 983 | 1217 | 266 / 275 | 25.7 / 33.2 | 63.8 | 4.4 | 0.0 % | 0.29 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 508 | 542 | 688 | 1027 | 406 / 424 | 19.1 / 24.5 | 88.3 | 6.1 | 0.0 % | 0.43 % | all arrays as {index: value} |
| json_full | orjson | 15959 | 15979 | 16004 | 16051 | 30.4 / 31.2 | 69.3 / 70.9 | – | – | 0.0 % | 0.10 % |  |
| json_merge_patch | orjson | 6302 | 6509 | 6705 | 7850 | 53.0 / 54.8 | 26.5 / 29.1 | 40.0 | 4.7 | 0.0 % | 0.08 % |  |
| cbor_full | cbor2 | 16816 | 16820 | 16821 | 16821 | 222 / 226 | 290 / 294 | – | – | 0.0 % | 0.51 % |  |
| cbor_merge_patch | cbor2 | 6189 | 6391 | 6543 | 7552 | 124 / 129 | 107 / 114 | 42.4 | 7.7 | 0.0 % | 0.23 % |  |
| msgpack_full | msgpack | 16861 | 16863 | 16867 | 16867 | 61.2 / 62.4 | 117 / 120 | – | – | 0.0 % | 0.18 % |  |
| msgpack_merge_patch | msgpack | 6226 | 6429 | 6579 | 7591 | 62.7 / 64.8 | 48.7 / 51.5 | 40.1 | 4.6 | 0.0 % | 0.11 % |  |
| fb_full | flatbuffers | 6261 | 6272 | 6280 | 6288 | 1769 / 1790 | 1793 / 1808 | – | – | 0.0 % | 3.56 % |  |
| fb_delta | flatbuffers | 1950 | 1992 | 2176 | 2464 | 767 / 798 | 832 / 852 | 767 | 832 | 0.0 % | 1.60 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8383 | 8383 | 8387 | 8387 | 649 / 663 | 103 / 106 | – | – | 0.0 % | 0.75 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 156 | 165 | 223 | 356 | 2134 / 2178 | 32.9 / 58.2 | 1675 | 25.6 | 1.7 % | 2.17 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14485 | 14505 | 14532 | 14585 | 48.1 / 49.8 | 58.1 / 58.8 | – | – | 0.0 % | 0.11 % |  |
| json_merge_patch | JSON | 5907 | 6101 | 6286 | 7394 | 66.7 / 69.6 | 23.4 / 25.3 | 45.0 | 0.8 | 0.0 % | 0.09 % |  |
| cbor_full | cbor-x | 11058 | 11065 | 11073 | 11105 | 89.2 / 90.5 | 130 / 131 | – | – | 0.0 % | 0.22 % |  |
| cbor_merge_patch | cbor-x | 4649 | 4798 | 4915 | 5754 | 89.1 / 91.7 | 43.9 / 45.9 | 44.2 | 0.8 | 0.0 % | 0.13 % |  |
| msgpack_full | @msgpack/msgpack | 10984 | 10991 | 11002 | 11034 | 119 / 122 | 87.8 / 88.8 | – | – | 0.0 % | 0.21 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4653 | 4803 | 4918 | 5744 | 93.8 / 96.3 | 36.0 / 37.6 | 44.1 | 0.8 | 0.0 % | 0.13 % |  |

