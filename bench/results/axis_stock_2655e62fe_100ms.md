Trace `axis_stock_2655e62fe_100ms`, 1384 ticks, poll period 0.1 s (budget per tick 100000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 16008 | 16030 | 16052 | 16098 | 212 / 214 | 355 / 360 | – | – | 0.0 % | 0.57 % |  |
| json_merge_patch | nlohmann | 6345 | 6560 | 6755 | 7911 | 392 / 396 | 156 / 164 | 43.8 | 39.4 | 0.0 % | 0.55 % |  |
| cbor_full | nlohmann | 13844 | 13852 | 13856 | 13872 | 185 / 188 | 337 / 340 | – | – | 0.0 % | 0.52 % |  |
| cbor_merge_patch | nlohmann | 5379 | 5559 | 5691 | 6605 | 376 / 380 | 134 / 141 | 42.5 | 34.2 | 0.0 % | 0.51 % |  |
| msgpack_full | nlohmann | 13889 | 13895 | 13903 | 13919 | 179 / 182 | 333 / 337 | – | – | 0.0 % | 0.51 % |  |
| msgpack_merge_patch | nlohmann | 5415 | 5597 | 5727 | 6643 | 371 / 375 | 133 / 140 | 42.5 | 34.0 | 0.0 % | 0.50 % |  |
| json_merge_patch_objidx_structs | nlohmann | 744 | 751 | 982 | 1218 | 447 / 468 | 20.4 / 28.9 | 51.3 | 4.8 | 0.0 % | 0.47 % |  |
| json_merge_patch_objidx_all | nlohmann | 508 | 542 | 686 | 1004 | 526 / 534 | 13.6 / 17.8 | 66.6 | 3.0 | 0.0 % | 0.54 % |  |
| fb_full | flatbuffers | 6364 | 6376 | 6384 | 6392 | 5.7 / 5.9 | 3.6 / 3.6 | – | – | 0.0 % | 0.01 % |  |
| fb_delta | flatbuffers | 1996 | 2040 | 2224 | 2544 | 2.9 / 3.1 | 1.9 / 2.0 | 2.9 | – | 0.0 % | 0.00 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 16008 | 16030 | 16052 | 16098 | 199 / 200 | 310 / 315 | – | – | 0.0 % | 0.51 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6364 | 6376 | 6384 | 6392 | 5.8 / 5.9 | 2.5 / 2.5 | – | – | 0.0 % | 0.01 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 16008 | 16030 | 16052 | 16098 | 200 / 204 | 280 / 284 | – | – | 0.0 % | 0.48 % |  |
| json_merge_patch | json | 6345 | 6560 | 6755 | 7911 | 120 / 127 | 102 / 109 | 41.0 | 5.1 | 0.0 % | 0.22 % |  |
| json_full_deflate | json+zlib | 313 | 324 | 373 | 1394 | 282 / 305 | 292 / 296 | – | – | 0.0 % | 0.57 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 199 | 204 | 328 | 430 | 159 / 186 | 109 / 118 | 41.4 | 5.4 | 0.0 % | 0.27 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6527 | 6525 | 6719 | 7878 | 117 / 123 | 100 / 106 | 39.4 | 4.7 | 3.3 % | 0.22 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6527 | 6525 | 6719 | 7878 | 622 / 638 | 105 / 111 | 335 | 5.2 | 3.3 % | 0.73 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 744 | 751 | 982 | 1218 | 260 / 270 | 25.3 / 32.8 | 62.4 | 4.2 | 0.0 % | 0.28 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 508 | 542 | 686 | 1004 | 404 / 421 | 19.0 / 24.5 | 88.4 | 6.0 | 0.0 % | 0.42 % | all arrays as {index: value} |
| json_full | orjson | 16008 | 16030 | 16052 | 16098 | 30.5 / 31.5 | 68.5 / 70.5 | – | – | 0.0 % | 0.10 % |  |
| json_merge_patch | orjson | 6345 | 6560 | 6755 | 7911 | 53.0 / 54.7 | 25.9 / 28.4 | 40.0 | 4.6 | 0.0 % | 0.08 % |  |
| cbor_full | cbor2 | 16816 | 16820 | 16821 | 16821 | 222 / 226 | 295 / 301 | – | – | 0.0 % | 0.52 % |  |
| cbor_merge_patch | cbor2 | 6185 | 6391 | 6543 | 7533 | 124 / 129 | 107 / 114 | 41.9 | 7.5 | 0.0 % | 0.23 % |  |
| msgpack_full | msgpack | 16861 | 16863 | 16867 | 16867 | 60.6 / 61.8 | 117 / 120 | – | – | 0.0 % | 0.18 % |  |
| msgpack_merge_patch | msgpack | 6221 | 6429 | 6579 | 7571 | 63.4 / 65.7 | 47.5 / 50.3 | 40.5 | 4.6 | 0.0 % | 0.11 % |  |
| fb_full | flatbuffers | 6259 | 6272 | 6280 | 6288 | 1763 / 1783 | 1792 / 1807 | – | – | 0.0 % | 3.55 % |  |
| fb_delta | flatbuffers | 1948 | 1992 | 2176 | 2472 | 762 / 796 | 834 / 854 | 762 | 834 | 0.0 % | 1.60 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8383 | 8383 | 8387 | 8387 | 650 / 658 | 103 / 105 | – | – | 0.0 % | 0.75 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 156 | 165 | 223 | 334 | 2095 / 2139 | 32.5 / 57.3 | 1644 | 25.2 | 1.7 % | 2.13 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 20

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14535 | 14558 | 14582 | 14635 | 47.7 / 49.8 | 57.9 / 58.4 | – | – | 0.0 % | 0.11 % |  |
| json_merge_patch | JSON | 5953 | 6154 | 6339 | 7455 | 65.5 / 68.4 | 23.3 / 25.3 | 43.8 | 0.8 | 0.0 % | 0.09 % |  |
| cbor_full | cbor-x | 11062 | 11072 | 11080 | 11108 | 87.3 / 89.1 | 129 / 130 | – | – | 0.0 % | 0.22 % |  |
| cbor_merge_patch | cbor-x | 4651 | 4805 | 4922 | 5767 | 88.8 / 91.3 | 43.2 / 45.2 | 43.8 | 0.8 | 0.0 % | 0.13 % |  |
| msgpack_full | @msgpack/msgpack | 10989 | 10999 | 11010 | 11034 | 117 / 119 | 87.9 / 89.1 | – | – | 0.0 % | 0.21 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4656 | 4811 | 4926 | 5757 | 92.5 / 95.2 | 35.3 / 37.1 | 43.5 | 0.8 | 0.0 % | 0.13 % |  |

