Trace `gmoccapy_2_tools_with_cutter_radius_compensation_100ms`, 431 ticks, poll period 0.1 s (budget per tick 100000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 15977 | 16037 | 16083 | 16111 | 222 / 242 | 403 / 429 | – | – | 0.0 % | 0.62 % |  |
| json_merge_patch | nlohmann | 5880 | 6536 | 6582 | 12024 | 449 / 466 | 178 / 198 | 49.5 | 49.6 | 0.0 % | 0.63 % |  |
| cbor_full | nlohmann | 13900 | 13913 | 13932 | 13932 | 196 / 213 | 389 / 407 | – | – | 0.0 % | 0.59 % |  |
| cbor_merge_patch | nlohmann | 5038 | 5575 | 5603 | 10461 | 438 / 463 | 160 / 181 | 49.8 | 42.1 | 0.0 % | 0.60 % |  |
| msgpack_full | nlohmann | 13942 | 13958 | 13972 | 13972 | 199 / 222 | 402 / 433 | – | – | 0.0 % | 0.60 % |  |
| msgpack_merge_patch | nlohmann | 5072 | 5613 | 5639 | 10493 | 466 / 522 | 172 / 206 | 52.8 | 46.5 | 0.0 % | 0.64 % |  |
| json_merge_patch_objidx_structs | nlohmann | 725 | 811 | 945 | 1433 | 502 / 535 | 29.1 / 34.0 | 59.8 | 7.0 | 0.0 % | 0.53 % |  |
| json_merge_patch_objidx_all | nlohmann | 572 | 574 | 829 | 1212 | 609 / 647 | 20.4 / 27.8 | 80.3 | 4.8 | 0.0 % | 0.63 % |  |
| fb_full | flatbuffers | 6390 | 6416 | 6440 | 6448 | 6.5 / 7.0 | 3.6 / 3.7 | – | – | 0.0 % | 0.01 % |  |
| fb_delta | flatbuffers | 1861 | 2040 | 2056 | 3328 | 3.2 / 3.6 | 1.9 / 1.9 | 3.2 | – | 0.0 % | 0.01 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 15977 | 16037 | 16083 | 16111 | 210 / 230 | 350 / 365 | – | – | 0.0 % | 0.56 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6390 | 6416 | 6440 | 6448 | 7.3 / 8.3 | 2.5 / 2.6 | – | – | 0.0 % | 0.01 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 15977 | 16037 | 16083 | 16111 | 287 / 335 | 294 / 343 | – | – | 0.0 % | 0.58 % |  |
| json_merge_patch | json | 5880 | 6536 | 6582 | 12024 | 171 / 226 | 110 / 147 | 60.0 | 7.1 | 0.0 % | 0.28 % |  |
| json_full_deflate | json+zlib | 337 | 356 | 432 | 1551 | 418 / 644 | 318 / 478 | – | – | 0.0 % | 0.74 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 213 | 232 | 303 | 772 | 234 / 319 | 124 / 166 | 62.1 | 8.3 | 0.0 % | 0.36 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6443 | 6504 | 6548 | 11987 | 170 / 213 | 109 / 148 | 58.6 | 6.8 | 9.3 % | 0.28 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6456 | 6504 | 6554 | 11987 | 831 / 929 | 117 / 148 | 453 | 8.2 | 9.1 % | 0.95 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 725 | 811 | 945 | 1433 | 378 / 422 | 30.1 / 42.5 | 84.3 | 6.2 | 0.0 % | 0.41 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 572 | 574 | 829 | 1212 | 580 / 677 | 30.1 / 45.0 | 116 | 9.1 | 0.0 % | 0.61 % | all arrays as {index: value} |
| json_full | orjson | 15977 | 16037 | 16083 | 16111 | 42.6 / 47.5 | 80.6 / 91.7 | – | – | 0.0 % | 0.12 % |  |
| json_merge_patch | orjson | 5880 | 6536 | 6582 | 12024 | 67.3 / 95.0 | 28.9 / 39.7 | 52.5 | 5.5 | 0.0 % | 0.10 % |  |
| cbor_full | cbor2 | 16859 | 16857 | 16868 | 16868 | 287 / 330 | 382 / 427 | – | – | 0.0 % | 0.67 % |  |
| cbor_merge_patch | cbor2 | 5785 | 6391 | 6412 | 12509 | 164 / 200 | 136 / 167 | 60.1 | 10.4 | 0.0 % | 0.30 % |  |
| msgpack_full | msgpack | 16900 | 16902 | 16908 | 16908 | 83.4 / 108 | 156 / 206 | – | – | 0.0 % | 0.24 % |  |
| msgpack_merge_patch | msgpack | 5819 | 6429 | 6450 | 12541 | 80.7 / 89.4 | 55.6 / 66.8 | 54.5 | 5.3 | 0.0 % | 0.14 % |  |
| fb_full | flatbuffers | 6294 | 6312 | 6336 | 6344 | 2244 / 2441 | 2300 / 2484 | – | – | 0.0 % | 4.54 % |  |
| fb_delta | flatbuffers | 1817 | 1992 | 2008 | 3280 | 962 / 1068 | 1026 / 1125 | 962 | 1026 | 0.0 % | 1.99 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8412 | 8413 | 8420 | 8420 | 823 / 901 | 126 / 148 | – | – | 0.0 % | 0.95 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 187 | 185 | 253 | 399 | 2846 / 3094 | 49.2 / 71.4 | 2216 | 36.4 | 4.7 % | 2.90 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14505 | 14570 | 14620 | 14651 | 61.0 / 66.3 | 68.7 / 74.1 | – | – | 0.0 % | 0.13 % |  |
| json_merge_patch | JSON | 5510 | 6133 | 6183 | 11008 | 101 / 109 | 28.1 / 31.9 | 74.4 | 1.6 | 0.0 % | 0.13 % |  |
| cbor_full | cbor-x | 11109 | 11134 | 11161 | 11169 | 124 / 130 | 188 / 201 | – | – | 0.0 % | 0.31 % |  |
| cbor_merge_patch | cbor-x | 4343 | 4822 | 4838 | 8540 | 140 / 158 | 58.4 / 65.1 | 76.7 | 1.7 | 0.0 % | 0.20 % |  |
| msgpack_full | @msgpack/msgpack | 11030 | 11056 | 11082 | 11090 | 156 / 173 | 139 / 151 | – | – | 0.0 % | 0.30 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4345 | 4827 | 4843 | 8485 | 140 / 161 | 53.2 / 57.8 | 77.6 | 1.7 | 0.0 % | 0.19 % |  |

