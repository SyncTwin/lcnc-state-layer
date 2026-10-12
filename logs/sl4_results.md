| case | client | action | got | expected | ok | note |
|---|---|---|---|---|---|---|
| 1 invalid | A | fly() | failed | failed | ✅ | unknown command 'fly' |
| 1 invalid | B | mode('MODE_BOGUS') | failed | failed | ✅ | CommandError: unknown constant 'MODE_BOGUS' (expected MODE_*) |
| 1 invalid | B | mdi() without argument | failed | failed | ✅ | TypeError: function takes exactly 1 argument (0 given) |
| 2 wrong state | B | unhome(0) in teleop mode | failed | failed | ✅ | must be in joint mode or disabled to unhome |
| 2 wrong state | A+B | error entry seen by both clients | 1/1 | both ≥1 | ✅ | must be in joint mode or disabled to unhome |
| 2 wrong state | A | mdi('G0 X10') in MODE_MANUAL | failed | failed | ✅ | RCS_ERROR: Must be in MDI mode to issue MDI command |
| 3 concurrent | A | 10× set_block_delete | ['completed'] | ['completed'] | ✅ | own ids only: True |
| 3 concurrent | B | 10× set_block_delete | ['completed'] | ['completed'] | ✅ | interleaved with A's in one sidecar queue |
| 4 mdi | A | mdi('G90 G0 X20 Y15') | completed | completed | ✅ | after 1.24 s |
| 4 mdi | raw stat | machine stopped at the moment of completed | vel=0 dtg=0 inpos=True interp=1 | vel=0 dtg=0 inpos interp=IDLE | ✅ | position [20.0, 15.0] = 20,15 + g5x_offset [0.0, 0.0] |
| 5 abort | B | abort() during run | completed | completed | ✅ |  |
| 5 abort | A | run(axis.ngc) aborted by B | aborted | aborted | ✅ |  |
| 5 abort | A | program_end.reason | aborted | aborted | ✅ |  |
| 6 completed | A | run(gmoccapy_2_tools_with_cutter_radius_compensation.ngc) | completed | completed | ✅ |  |
| 6 completed | B | program_end.reason seen by B | completed | completed | ✅ |  |
| 7 error | A | run(error_test.ngc) | failed | failed | ✅ | RCS_ERROR: invalid params in linear command |
| 7 error | B | program_end.reason seen by B | error | error | ✅ | Linear move on line 5 would exceed X's positive limit; Linear move on line 5 would exceed joint 0's positive limit max:[254.000000]; invalid params in linear command |
| 8 expect_file | A | run(expect_file=other) | failed | failed | ✅ | loaded program '/home/user/lcnc-state-layer/sim/error_test.ngc' is not the expected '/nonexistent/other.ngc' |
| 9 foreign writer | B | 58× program_open(nonexistent) while another client writes | {'failed': 58} | no completed | ✅ | accepted = echo moved past our serial before its status was seen |
| 9 foreign writer | raw emcmodule | c1.mdi() in MANUAL (fails), c2 command, c1.wait_complete() | 1 | 1 (=RCS_DONE: the mine) | ✅ | writer: mine demo: task_mode=1, c1.mdi() serial=1908, c2 serial=1909, echo=1909, c1.wait_complete() -> 1 (RCS_DONE=1, RCS_ERROR=3) |
| 10 second reader | sidecar vs reader | 20 failing program_open, other reader polls every 0.2 s | sidecar 40, other reader 0 | sum = all errors | ✅ | error_channel is a single-consumer queue (cms_in.cc:817-828): an entry goes to whichever reader polls first |
| 10 second reader | sidecar vs reader | 20 failing program_open, other reader polls every 0.005 s | sidecar 0, other reader 40 | sum = all errors | ✅ | error_channel is a single-consumer queue (cms_in.cc:817-828): an entry goes to whichever reader polls first |
| 11 view state | A2 (key A) | snapshot.view_state on connect | {'tab': 'auto', 'zoom': 1.5} | {'tab': 'auto', 'zoom': 1.5} | ✅ |  |
| 11 view state | A2 (key A) | view_state pushed when A changes it | {'tab': 'auto', 'zoom': 2.0} | {'tab': 'auto', 'zoom': 2.0} | ✅ |  |
| 11 view state | A (reconnect) | own blob back | {'tab': 'auto', 'zoom': 2.0} | {'tab': 'auto', 'zoom': 2.0} | ✅ |  |
| 11 view state | B (reconnect) | own blob back | {'tab': 'mdi', 'dro': 'machine'} | {'tab': 'mdi', 'dro': 'machine'} | ✅ |  |
| 11 view state | B | 70 KiB blob refused, old blob kept | {'tab': 'mdi', 'dro': 'machine'} | {'tab': 'mdi', 'dro': 'machine'} | ✅ | limit 64 KiB (ASSUMPTION, not measured) |
| 12 read-only | R | command to a sidecar without --allow-commands | failed | failed | ✅ | commands disabled: sidecar runs read-only, start it with --allow-commands |

28 checks, 0 failed
