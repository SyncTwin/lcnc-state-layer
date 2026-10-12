Trace `axis_stock_2655e62fe_20ms`, 6886 ticks, poll period 0.02 s (budget per tick 20000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 16025 | 16034 | 16062 | 16120 | 298 / 310 | 529 / 532 | – | – | 0.0 % | 4.14 % |  |
| json_merge_patch | nlohmann | 6402 | 6562 | 6605 | 8045 | 564 / 571 | 240 / 244 | 69.2 | 52.6 | 0.0 % | 4.02 % |  |
| cbor_full | nlohmann | 13850 | 13852 | 13856 | 13872 | 267 / 283 | 494 / 500 | – | – | 0.0 % | 3.80 % |  |
| cbor_merge_patch | nlohmann | 5426 | 5559 | 5580 | 6684 | 546 / 552 | 191 / 194 | 68.6 | 47.1 | 0.0 % | 3.68 % |  |
| msgpack_full | nlohmann | 13895 | 13895 | 13903 | 13919 | 265 / 268 | 493 / 499 | – | – | 0.0 % | 3.79 % |  |
| msgpack_merge_patch | nlohmann | 5463 | 5597 | 5618 | 6722 | 552 / 559 | 191 / 198 | 69.0 | 47.3 | 0.0 % | 3.71 % |  |
| json_merge_patch_objidx_structs | nlohmann | 731 | 750 | 830 | 1218 | 660 / 669 | 32.1 / 39.2 | 77.8 | 6.5 | 0.0 % | 3.46 % |  |
| json_merge_patch_objidx_all | nlohmann | 497 | 541 | 620 | 977 | 784 / 801 | 20.4 / 23.6 | 104 | 4.4 | 0.0 % | 4.02 % |  |
| fb_full | flatbuffers | 6372 | 6376 | 6384 | 6392 | 9.4 / 9.9 | 4.3 / 4.3 | – | – | 0.0 % | 0.07 % |  |
| fb_delta | flatbuffers | 1998 | 2040 | 2048 | 2568 | 5.0 / 5.4 | 2.1 / 2.1 | 5.0 | – | 0.0 % | 0.04 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 16025 | 16034 | 16062 | 16120 | 281 / 283 | 467 / 470 | – | – | 0.0 % | 3.74 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6372 | 6376 | 6384 | 6392 | 9.3 / 9.9 | 2.8 / 2.8 | – | – | 0.0 % | 0.06 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 16025 | 16034 | 16062 | 16120 | 352 / 357 | 284 / 286 | – | – | 0.0 % | 3.18 % |  |
| json_merge_patch | json | 6402 | 6562 | 6605 | 8045 | 201 / 206 | 107 / 109 | 67.0 | 6.8 | 0.0 % | 1.54 % |  |
| json_full_deflate | json+zlib | 305 | 318 | 356 | 1571 | 483 / 506 | 302 / 306 | – | – | 0.0 % | 3.93 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 185 | 197 | 244 | 806 | 261 / 290 | 117 / 120 | 67.3 | 7.4 | 0.0 % | 1.89 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6519 | 6525 | 6569 | 8008 | 198 / 203 | 106 / 108 | 64.4 | 6.3 | 2.4 % | 1.52 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6518 | 6525 | 6569 | 8008 | 889 / 915 | 107 / 109 | 468 | 6.7 | 2.4 % | 4.98 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 731 | 750 | 830 | 1218 | 403 / 411 | 23.7 / 26.2 | 90.7 | 5.5 | 0.0 % | 2.13 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 497 | 541 | 620 | 977 | 605 / 623 | 21.4 / 24.3 | 127 | 8.0 | 0.0 % | 3.13 % | all arrays as {index: value} |
| cbor_full | cbor2 | 16819 | 16820 | 16821 | 16821 | 304 / 307 | 388 / 393 | – | – | 0.0 % | 3.46 % |  |
| cbor_merge_patch | cbor2 | 6239 | 6391 | 6412 | 7600 | 178 / 182 | 143 / 145 | 66.2 | 10.3 | 0.0 % | 1.60 % |  |
| msgpack_full | msgpack | 16864 | 16863 | 16867 | 16867 | 116 / 118 | 167 / 169 | – | – | 0.0 % | 1.41 % |  |
| msgpack_merge_patch | msgpack | 6276 | 6429 | 6450 | 7638 | 108 / 112 | 64.2 / 65.4 | 66.9 | 6.2 | 0.0 % | 0.86 % |  |
| fb_full | flatbuffers | 6267 | 6272 | 6280 | 6288 | 2481 / 2513 | 2615 / 2648 | – | – | 0.0 % | 25.48 % |  |
| fb_delta | flatbuffers | 1950 | 1992 | 2000 | 2496 | 1090 / 1122 | 1206 / 1233 | 1090 | 1206 | 0.0 % | 11.48 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8384 | 8383 | 8387 | 8387 | 982 / 1003 | 166 / 167 | – | – | 0.0 % | 5.74 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 150 | 165 | 191 | 334 | 2873 / 2919 | 47.3 / 49.7 | 2211 | 35.6 | 1.2 % | 14.60 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

