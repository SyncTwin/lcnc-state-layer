Trace `axis_stock_2655e62fe_100ms`, 1384 ticks, poll period 0.1 s (budget per tick 100000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 16008 | 16030 | 16052 | 16098 | 295 / 296 | 526 / 533 | – | – | 0.0 % | 0.82 % |  |
| json_merge_patch | nlohmann | 6345 | 6560 | 6755 | 7911 | 532 / 536 | 234 / 246 | 59.0 | 53.8 | 0.0 % | 0.77 % |  |
| cbor_full | nlohmann | 13844 | 13852 | 13856 | 13872 | 262 / 263 | 481 / 484 | – | – | 0.0 % | 0.74 % |  |
| cbor_merge_patch | nlohmann | 5379 | 5559 | 5691 | 6605 | 517 / 521 | 194 / 204 | 59.6 | 47.1 | 0.0 % | 0.71 % |  |
| msgpack_full | nlohmann | 13889 | 13895 | 13903 | 13919 | 261 / 262 | 474 / 476 | – | – | 0.0 % | 0.73 % |  |
| msgpack_merge_patch | nlohmann | 5415 | 5597 | 5727 | 6643 | 514 / 520 | 196 / 205 | 57.8 | 48.1 | 0.0 % | 0.71 % |  |
| json_merge_patch_objidx_structs | nlohmann | 744 | 751 | 982 | 1218 | 617 / 650 | 29.1 / 41.0 | 69.8 | 6.2 | 0.0 % | 0.65 % |  |
| json_merge_patch_objidx_all | nlohmann | 508 | 542 | 686 | 1004 | 773 / 796 | 19.8 / 26.0 | 94.1 | 4.3 | 0.0 % | 0.79 % |  |
| fb_full | flatbuffers | 6364 | 6376 | 6384 | 6392 | 9.4 / 9.9 | 4.3 / 4.3 | – | – | 0.0 % | 0.01 % |  |
| fb_delta | flatbuffers | 1996 | 2040 | 2224 | 2544 | 5.0 / 5.5 | 2.1 / 2.2 | 5.0 | – | 0.0 % | 0.01 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 16008 | 16030 | 16052 | 16098 | 279 / 281 | 461 / 463 | – | – | 0.0 % | 0.74 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6364 | 6376 | 6384 | 6392 | 9.2 / 9.7 | 2.8 / 2.8 | – | – | 0.0 % | 0.01 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 16008 | 16030 | 16052 | 16098 | 354 / 358 | 285 / 287 | – | – | 0.0 % | 0.64 % |  |
| json_merge_patch | json | 6345 | 6560 | 6755 | 7911 | 201 / 209 | 107 / 114 | 65.4 | 7.1 | 0.0 % | 0.31 % |  |
| json_full_deflate | json+zlib | 313 | 324 | 373 | 1394 | 486 / 510 | 303 / 307 | – | – | 0.0 % | 0.79 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 199 | 204 | 328 | 430 | 265 / 297 | 117 / 129 | 67.0 | 7.6 | 0.0 % | 0.38 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6527 | 6525 | 6719 | 7878 | 201 / 209 | 107 / 114 | 65.1 | 6.6 | 3.3 % | 0.31 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6527 | 6525 | 6719 | 7878 | 897 / 920 | 108 / 115 | 471 | 7.0 | 3.3 % | 1.00 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 744 | 751 | 982 | 1218 | 403 / 415 | 23.9 / 32.7 | 90.8 | 5.5 | 0.0 % | 0.43 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 508 | 542 | 686 | 1004 | 606 / 631 | 21.5 / 27.9 | 127 | 8.0 | 0.0 % | 0.63 % | all arrays as {index: value} |
| cbor_full | cbor2 | 16816 | 16820 | 16821 | 16821 | 307 / 311 | 391 / 395 | – | – | 0.0 % | 0.70 % |  |
| cbor_merge_patch | cbor2 | 6185 | 6391 | 6543 | 7533 | 177 / 185 | 144 / 152 | 65.6 | 10.4 | 0.0 % | 0.32 % |  |
| msgpack_full | msgpack | 16861 | 16863 | 16867 | 16867 | 116 / 118 | 164 / 166 | – | – | 0.0 % | 0.28 % |  |
| msgpack_merge_patch | msgpack | 6221 | 6429 | 6579 | 7571 | 107 / 112 | 64.3 / 68.5 | 66.3 | 6.2 | 0.0 % | 0.17 % |  |
| fb_full | flatbuffers | 6259 | 6272 | 6280 | 6288 | 2479 / 2523 | 2562 / 2605 | – | – | 0.0 % | 5.04 % |  |
| fb_delta | flatbuffers | 1948 | 1992 | 2176 | 2472 | 1084 / 1126 | 1193 / 1218 | 1084 | 1193 | 0.0 % | 2.28 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8383 | 8383 | 8387 | 8387 | 982 / 997 | 159 / 160 | – | – | 0.0 % | 1.14 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 156 | 165 | 223 | 334 | 2878 / 2952 | 45.9 / 81.0 | 2231 | 35.8 | 1.7 % | 2.92 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

