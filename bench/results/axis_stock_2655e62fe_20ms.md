Trace `axis_stock_2655e62fe_20ms`, 6886 ticks, poll period 0.02 s (budget per tick 20000 µs). Bytes per message sent; CPU per message in µs (median / p95 over messages, each the median of the repeats); empty = share of ticks with nothing to send.

#### C++ (nlohmann/json 3.11, flatbuffers 2.0.8, -O2), repeats 5

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | nlohmann | 16025 | 16034 | 16062 | 16120 | 204 / 210 | 356 / 366 | – | – | 0.0 % | 2.80 % |  |
| json_merge_patch | nlohmann | 6402 | 6562 | 6605 | 8045 | 392 / 403 | 151 / 158 | 46.7 | 35.7 | 0.0 % | 2.72 % |  |
| cbor_full | nlohmann | 13850 | 13852 | 13856 | 13872 | 184 / 209 | 342 / 376 | – | – | 0.0 % | 2.63 % |  |
| cbor_merge_patch | nlohmann | 5426 | 5559 | 5580 | 6684 | 373 / 386 | 127 / 134 | 45.4 | 33.2 | 0.0 % | 2.50 % |  |
| msgpack_full | nlohmann | 13895 | 13895 | 13903 | 13919 | 178 / 185 | 334 / 342 | – | – | 0.0 % | 2.56 % |  |
| msgpack_merge_patch | nlohmann | 5463 | 5597 | 5618 | 6722 | 373 / 383 | 129 / 135 | 44.1 | 33.5 | 0.0 % | 2.51 % |  |
| json_merge_patch_objidx_structs | nlohmann | 731 | 750 | 830 | 1218 | 455 / 489 | 20.8 / 24.6 | 51.6 | 5.0 | 0.0 % | 2.38 % |  |
| json_merge_patch_objidx_all | nlohmann | 497 | 541 | 620 | 977 | 558 / 608 | 13.8 / 17.4 | 68.2 | 3.1 | 0.0 % | 2.86 % |  |
| fb_full | flatbuffers | 6372 | 6376 | 6384 | 6392 | 5.7 / 6.1 | 3.6 / 3.7 | – | – | 0.0 % | 0.05 % |  |
| fb_delta | flatbuffers | 1998 | 2040 | 2048 | 2568 | 3.0 / 3.3 | 2.0 / 2.0 | 3.0 | – | 0.0 % | 0.03 % | EmcStatDelta: changed fields only (optional scalars), arrays whole |
| json_full_read5 | nlohmann | 16025 | 16034 | 16062 | 16120 | 203 / 212 | 318 / 330 | – | – | 0.0 % | 2.61 % | decode = parse to DOM + read the same 5 fields |
| fb_full_read5 | flatbuffers | 6372 | 6376 | 6384 | 6392 | 7.2 / 7.5 | 3.1 / 3.1 | – | – | 0.0 % | 0.05 % | decode = verify + read task_state, interp_state, motion_line, current_vel, position |

#### Python (stdlib json, orjson, cbor2, msgpack, flatbuffers, protobuf), repeats 2

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | json | 16025 | 16034 | 16062 | 16120 | 201 / 226 | 283 / 313 | – | – | 0.0 % | 2.42 % |  |
| json_merge_patch | json | 6402 | 6562 | 6605 | 8045 | 122 / 147 | 105 / 128 | 41.3 | 5.6 | 0.0 % | 1.14 % |  |
| json_full_deflate | json+zlib | 305 | 318 | 356 | 1571 | 297 / 333 | 297 / 332 | – | – | 0.0 % | 2.97 % | permessage-deflate simulated: raw deflate, context takeover, level 6 |
| json_merge_patch_deflate | json+zlib | 185 | 197 | 244 | 806 | 162 / 190 | 112 / 122 | 42.1 | 5.6 | 0.0 % | 1.37 % | permessage-deflate simulated (RFC 7692) |
| json_merge_patch_no_beats | json | 6519 | 6525 | 6569 | 8008 | 119 / 128 | 104 / 112 | 39.8 | 4.9 | 2.4 % | 1.11 % | heartbeat, taskbeat dropped (sidecar --drop-fields) |
| json_merge_patch_no_beats_deadband | json | 6518 | 6525 | 6569 | 8008 | 631 / 667 | 108 / 120 | 340 | 5.4 | 2.4 % | 3.70 % | + float deadband 1e-4 (mkwrapper threshold) |
| json_merge_patch_objidx_structs | json | 731 | 750 | 830 | 1218 | 265 / 275 | 25.8 / 29.4 | 63.4 | 4.3 | 0.0 % | 1.46 % | arrays of objects as {index: obj} |
| json_merge_patch_objidx_all | json | 497 | 541 | 620 | 977 | 406 / 449 | 19.7 / 25.7 | 87.4 | 6.1 | 0.0 % | 2.13 % | all arrays as {index: value} |
| json_full | orjson | 16025 | 16034 | 16062 | 16120 | 31.0 / 33.2 | 69.0 / 72.6 | – | – | 0.0 % | 0.50 % |  |
| json_merge_patch | orjson | 6402 | 6562 | 6605 | 8045 | 53.4 / 58.7 | 26.5 / 30.0 | 40.4 | 4.7 | 0.0 % | 0.40 % |  |
| cbor_full | cbor2 | 16819 | 16820 | 16821 | 16821 | 223 / 260 | 291 / 336 | – | – | 0.0 % | 2.57 % |  |
| cbor_merge_patch | cbor2 | 6239 | 6391 | 6412 | 7600 | 124 / 130 | 107 / 113 | 40.9 | 7.4 | 0.0 % | 1.15 % |  |
| msgpack_full | msgpack | 16864 | 16863 | 16867 | 16867 | 61.8 / 70.3 | 119 / 139 | – | – | 0.0 % | 0.90 % |  |
| msgpack_merge_patch | msgpack | 6276 | 6429 | 6450 | 7638 | 63.0 / 70.9 | 48.5 / 54.6 | 40.4 | 4.7 | 0.0 % | 0.56 % |  |
| fb_full | flatbuffers | 6267 | 6272 | 6280 | 6288 | 1781 / 1857 | 1805 / 1873 | – | – | 0.0 % | 17.93 % |  |
| fb_delta | flatbuffers | 1950 | 1992 | 2000 | 2496 | 768 / 820 | 835 / 877 | 768 | 835 | 0.0 % | 8.01 % | EmcStatDelta: changed fields only, arrays whole |
| pb_machinetalk_full | protobuf | 8384 | 8383 | 8387 | 8387 | 667 / 687 | 105 / 111 | – | – | 0.0 % | 3.86 % | Machinetalk status.proto, motion+io+task+interp |
| pb_machinetalk_incremental | protobuf | 150 | 165 | 191 | 334 | 2191 / 2397 | 36.0 / 45.9 | 1703 | 27.0 | 1.2 % | 11.14 % | mkwrapper style: changed fields, repeated by index, float threshold 1e-4 |

#### JavaScript in node (browser code path), repeats 10

| variant | lib | bytes mean | p50 | p95 | max | encode med / p95 | decode med / p95 | diff med | apply med | empty | enc+dec of tick | note |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| json_full | JSON | 14553 | 14562 | 14592 | 14658 | 48.5 / 50.8 | 58.3 / 59.3 | – | – | 0.0 % | 0.53 % |  |
| json_merge_patch | JSON | 6006 | 6156 | 6202 | 7597 | 65.9 / 69.1 | 23.5 / 24.4 | 44.0 | 0.8 | 0.0 % | 0.45 % |  |
| cbor_full | cbor-x | 11071 | 11072 | 11082 | 11112 | 90.4 / 93.2 | 131 / 136 | – | – | 0.0 % | 1.11 % |  |
| cbor_merge_patch | cbor-x | 4693 | 4805 | 4831 | 5865 | 88.2 / 91.7 | 44.2 / 45.3 | 43.9 | 0.8 | 0.0 % | 0.66 % |  |
| msgpack_full | @msgpack/msgpack | 10998 | 11002 | 11011 | 11042 | 119 / 122 | 88.8 / 91.9 | – | – | 0.0 % | 1.04 % |  |
| msgpack_merge_patch | @msgpack/msgpack | 4698 | 4811 | 4835 | 5856 | 94.7 / 98.1 | 35.6 / 36.9 | 44.4 | 0.8 | 0.0 % | 0.65 % |  |

