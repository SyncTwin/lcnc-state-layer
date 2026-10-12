Trace `axis_20ms`, 6825 ticks, poll period 0.02 s (budget per tick 20000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 16008 | 16030 | 16053 | 16087 | 204 / 210 | 358 / 368 | – | – | 0.0 % | 2.81 % |  |
| json_merge_patch | nlohmann | 6379 | 6555 | 6588 | 7891 | 390 / 407 | 152 / 160 | 46.3 | 35.8 | 0.0 % | 2.71 % |  |
| cbor_full | nlohmann | 13872 | 13877 | 13878 | 13885 | 182 / 187 | 336 / 343 | – | – | 0.0 % | 2.59 % |  |
| cbor_merge_patch | nlohmann | 5434 | 5575 | 5588 | 6628 | 374 / 392 | 127 / 135 | 45.3 | 33.3 | 0.0 % | 2.50 % |  |
| msgpack_full | nlohmann | 13916 | 13919 | 13923 | 13931 | 178 / 184 | 340 / 347 | – | – | 0.0 % | 2.59 % |  |
| msgpack_merge_patch | nlohmann | 5471 | 5613 | 5626 | 6667 | 374 / 387 | 128 / 135 | 46.3 | 33.5 | 0.0 % | 2.51 % |  |
| json_merge_patch_objidx_structs | nlohmann | 751 | 778 | 858 | 1195 | 446 / 467 | 20.6 / 23.1 | 50.7 | 4.8 | 0.0 % | 2.33 % |  |
| json_merge_patch_objidx_all | nlohmann | 495 | 540 | 620 | 982 | 536 / 558 | 13.4 / 15.4 | 66.6 | 2.9 | 0.0 % | 2.75 % |  |
| fb_full | flatbuffers | 6379 | 6384 | 6392 | 6400 | 5.7 / 6.0 | 3.6 / 3.7 | – | – | 0.0 % | 0.05 % |  |
| fb_delta | flatbuffers | 1997 | 2040 | 2048 | 2520 | 3.0 / 3.3 | 2.0 / 2.0 | 3.0 | – | 0.0 % | 0.03 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 16008 | 16030 | 16053 | 16087 | 208 / 220 | 315 / 331 | – | – | 0.0 % | 2.61 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6379 | 6384 | 6392 | 6400 | 5.7 / 6.2 | 2.4 / 2.5 | – | – | 0.0 % | 0.04 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 2

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 16008 | 16030 | 16053 | 16087 | 218 / 247 | 291 / 324 | – | – | 0.0 % | 2.54 % |  |
| json_merge_patch | json | 6379 | 6555 | 6588 | 7891 | 133 / 156 | 108 / 125 | 44.0 | 5.7 | 0.0 % | 1.20 % |  |
| json_full_deflate | json+zlib | 304 | 318 | 355 | 1535 | 313 / 353 | 303 / 338 | – | – | 0.0 % | 3.08 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 186 | 198 | 247 | 594 | 174 / 211 | 114 / 130 | 44.8 | 5.9 | 0.0 % | 1.44 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6502 | 6519 | 6552 | 7854 | 130 / 149 | 107 / 121 | 42.6 | 5.4 | 2.5 % | 1.19 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6502 | 6519 | 6552 | 7854 | 640 / 666 | 108 / 115 | 345 | 5.5 | 2.4 % | 3.74 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 751 | 778 | 858 | 1195 | 268 / 297 | 27.6 / 33.5 | 63.2 | 4.4 | 0.0 % | 1.48 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 495 | 540 | 620 | 982 | 407 / 434 | 20.5 / 25.3 | 88.4 | 6.2 | 0.0 % | 2.14 % | all arrays as {index: value} |
| json_full | orjson | 16008 | 16030 | 16053 | 16087 | 30.5 / 33.5 | 68.7 / 76.8 | – | – | 0.0 % | 0.50 % |  |
| json_merge_patch | orjson | 6379 | 6555 | 6588 | 7891 | 53.5 / 57.0 | 25.8 / 28.5 | 40.5 | 4.5 | 0.0 % | 0.40 % |  |
| cbor_full | cbor2 | 16821 | 16821 | 16822 | 16863 | 224 / 253 | 289 / 324 | – | – | 0.0 % | 2.56 % |  |
| cbor_merge_patch | cbor2 | 6233 | 6391 | 6412 | 7552 | 125 / 140 | 106 / 118 | 42.2 | 7.8 | 0.0 % | 1.16 % |  |
| msgpack_full | msgpack | 16865 | 16863 | 16867 | 16906 | 61.8 / 70.3 | 118 / 138 | – | – | 0.0 % | 0.90 % |  |
| msgpack_merge_patch | msgpack | 6270 | 6429 | 6450 | 7591 | 63.5 / 71.2 | 47.8 / 54.5 | 40.9 | 4.6 | 0.0 % | 0.56 % |  |
| fb_full | flatbuffers | 6274 | 6280 | 6288 | 6296 | 1773 / 1870 | 1826 / 1915 | – | – | 0.0 % | 18.00 % |  |
| fb_delta | flatbuffers | 1948 | 1992 | 2000 | 2448 | 767 / 827 | 842 / 892 | 767 | 842 | 0.0 % | 8.05 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8376 | 8374 | 8378 | 8419 | 680 / 763 | 108 / 124 | – | – | 0.0 % | 3.94 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 149 | 165 | 191 | 337 | 2208 / 2333 | 36.5 / 47.0 | 1715 | 27.2 | 1.2 % | 11.22 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 10

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14543 | 14566 | 14591 | 14627 | 49.6 / 52.7 | 59.2 / 61.8 | – | – | 0.0 % | 0.54 % |  |
| json_merge_patch | JSON | 5986 | 6153 | 6187 | 7445 | 67.0 / 71.1 | 23.8 / 25.2 | 44.6 | 0.8 | 0.0 % | 0.45 % |  |
| cbor_full | cbor-x | 11100 | 11106 | 11114 | 11123 | 92.0 / 94.7 | 131 / 136 | – | – | 0.0 % | 1.12 % |  |
| cbor_merge_patch | cbor-x | 4700 | 4822 | 4838 | 5790 | 90.7 / 94.4 | 44.5 / 46.1 | 44.8 | 0.8 | 0.0 % | 0.68 % |  |
| msgpack_full | @msgpack/msgpack | 11025 | 11029 | 11037 | 11050 | 120 / 124 | 88.9 / 92.7 | – | – | 0.0 % | 1.04 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4705 | 4827 | 4843 | 5778 | 94.6 / 99.5 | 36.3 / 38.0 | 44.7 | 0.8 | 0.0 % | 0.65 % |  |

