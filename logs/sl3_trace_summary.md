### axis_100ms.jsonl.gz

- ticks: 1383, duration 138.2 s, period 0.100 s (--period)
- file: 395556 bytes gzip; fields per tick: 91; LinuxCNC 2.10.0~pre2
- schema `emc_stat.schema.json`: 0 of 1383 ticks invalid
- standing still (current_vel == 0, inpos, previous tick also 0): 34 tick pairs; position fields changed anyway: none
- fields changing between consecutive ticks (count of 1382 pairs):

| field | changed | share |
|---|---:|---:|
| `heartbeat` | 1382 | 100.0 % |
| `taskbeat` | 1382 | 100.0 % |
| `joint` | 1334 | 96.5 % |
| `joint_position` | 1332 | 96.4 % |
| `actual_position` | 1331 | 96.3 % |
| `joint_actual_position` | 1331 | 96.3 % |
| `position` | 1331 | 96.3 % |
| `distance_to_go` | 1308 | 94.6 % |
| `dtg` | 1308 | 94.6 % |
| `gcodes` | 186 | 13.5 % |
| `mcodes` | 186 | 13.5 % |
| `motion_id` | 186 | 13.5 % |
| `settings` | 186 | 13.5 % |
| `motion_line` | 185 | 13.4 % |
| `current_vel` | 71 | 5.1 % |
| `active_queue` | 50 | 3.6 % |
| `motion_type` | 38 | 2.7 % |
| `inpos` | 10 | 0.7 % |
| `state` | 10 | 0.7 % |
| `echo_serial_number` | 5 | 0.4 % |
| `queue` | 5 | 0.4 % |
| `current_line` | 4 | 0.3 % |
| `exec_state` | 4 | 0.3 % |
| `homed` | 3 | 0.2 % |
| `motion_mode` | 2 | 0.1 % |
| `interp_state` | 2 | 0.1 % |
| `read_line` | 2 | 0.1 % |
| `spindle` | 2 | 0.1 % |
| `enabled` | 1 | 0.1 % |
| `estop` | 1 | 0.1 % |
| `task_state` | 1 | 0.1 % |
| `optional_stop` | 1 | 0.1 % |
| `file` | 1 | 0.1 % |
| `task_mode` | 1 | 0.1 % |
| `command` | 1 | 0.1 % |

- never changed (56): `acceleration`, `adaptive_feed_enabled`, `ain`, `angular_units`, `aout`, `axis`, `axis_mask`, `block_delete`, `call_level`, `call_stack`, `cycle_time`, `debug`, `delay_left`, `din`, `dout`, `feed_hold_enabled`, `feed_override_enabled`, `feedrate`, `flood`, `g5x_index`, `g5x_offset`, `g68_active`, `g68_offset`, `g68_rotation`, `g92_offset`, `ini_filename`, `input_timeout`, `interpreter_errcode`, `joints`, `kinematics_type`, `limit`, `linear_units`, `max_acceleration`, `max_velocity`, `misc_error`, `mist`, `num_extrajoints`, `paused`, `pocket_prepped`, `probe_tripped`, `probe_val`, `probed_position`, `probing`, `program_units`, `queue_full`, `queued_mdi_commands`, `rapidrate`, `rotation_xy`, `single_stepping`, `spindles`, `task_paused`, `tool_from_pocket`, `tool_in_spindle`, `tool_offset`, `tool_table`, `velocity`

### gmoccapy_2_tools_with_cutter_radius_compensation_100ms.jsonl.gz

- ticks: 431, duration 43.0 s, period 0.100 s (--period)
- file: 134886 bytes gzip; fields per tick: 91; LinuxCNC 2.10.0~pre2
- schema `emc_stat.schema.json`: 0 of 431 ticks invalid
- standing still (current_vel == 0, inpos, previous tick also 0): 34 tick pairs; position fields changed anyway: none
- fields changing between consecutive ticks (count of 430 pairs):

| field | changed | share |
|---|---:|---:|
| `heartbeat` | 430 | 100.0 % |
| `taskbeat` | 430 | 100.0 % |
| `actual_position` | 386 | 89.8 % |
| `distance_to_go` | 386 | 89.8 % |
| `dtg` | 386 | 89.8 % |
| `joint` | 386 | 89.8 % |
| `joint_actual_position` | 386 | 89.8 % |
| `joint_position` | 386 | 89.8 % |
| `position` | 386 | 89.8 % |
| `current_vel` | 34 | 7.9 % |
| `motion_id` | 18 | 4.2 % |
| `motion_line` | 17 | 4.0 % |
| `gcodes` | 16 | 3.7 % |
| `mcodes` | 16 | 3.7 % |
| `settings` | 16 | 3.7 % |
| `motion_type` | 12 | 2.8 % |
| `queue` | 8 | 1.9 % |
| `current_line` | 7 | 1.6 % |
| `echo_serial_number` | 5 | 1.2 % |
| `command` | 4 | 0.9 % |
| `active_queue` | 4 | 0.9 % |
| `exec_state` | 4 | 0.9 % |
| `pocket_prepped` | 4 | 0.9 % |
| `read_line` | 4 | 0.9 % |
| `spindle` | 4 | 0.9 % |
| `interp_state` | 3 | 0.7 % |
| `motion_mode` | 2 | 0.5 % |
| `task_mode` | 2 | 0.5 % |
| `inpos` | 2 | 0.5 % |
| `state` | 2 | 0.5 % |
| `tool_from_pocket` | 2 | 0.5 % |
| `tool_in_spindle` | 2 | 0.5 % |
| `tool_offset` | 2 | 0.5 % |
| `tool_table` | 2 | 0.5 % |
| `flood` | 2 | 0.5 % |
| `mist` | 2 | 0.5 % |
| `file` | 1 | 0.2 % |

- never changed (54): `acceleration`, `adaptive_feed_enabled`, `ain`, `angular_units`, `aout`, `axis`, `axis_mask`, `block_delete`, `call_level`, `call_stack`, `cycle_time`, `debug`, `delay_left`, `din`, `dout`, `enabled`, `estop`, `feed_hold_enabled`, `feed_override_enabled`, `feedrate`, `g5x_index`, `g5x_offset`, `g68_active`, `g68_offset`, `g68_rotation`, `g92_offset`, `homed`, `ini_filename`, `input_timeout`, `interpreter_errcode`, `joints`, `kinematics_type`, `limit`, `linear_units`, `max_acceleration`, `max_velocity`, `misc_error`, `num_extrajoints`, `optional_stop`, `paused`, `probe_tripped`, `probe_val`, `probed_position`, `probing`, `program_units`, `queue_full`, `queued_mdi_commands`, `rapidrate`, `rotation_xy`, `single_stepping`, `spindles`, `task_paused`, `task_state`, `velocity`

### axis_20ms.jsonl.gz

- ticks: 6825, duration 136.5 s, period 0.020 s (--period)
- file: 1874436 bytes gzip; fields per tick: 91; LinuxCNC 2.10.0~pre2
- schema `emc_stat.schema.json`: 0 of 6825 ticks invalid
- standing still (current_vel == 0, inpos, previous tick also 0): 168 tick pairs; position fields changed anyway: none
- fields changing between consecutive ticks (count of 6824 pairs):

| field | changed | share |
|---|---:|---:|
| `taskbeat` | 6824 | 100.0 % |
| `heartbeat` | 6823 | 100.0 % |
| `actual_position` | 6649 | 97.4 % |
| `distance_to_go` | 6649 | 97.4 % |
| `dtg` | 6649 | 97.4 % |
| `joint` | 6649 | 97.4 % |
| `joint_actual_position` | 6649 | 97.4 % |
| `joint_position` | 6649 | 97.4 % |
| `position` | 6649 | 97.4 % |
| `motion_line` | 186 | 2.7 % |
| `gcodes` | 186 | 2.7 % |
| `mcodes` | 186 | 2.7 % |
| `motion_id` | 186 | 2.7 % |
| `settings` | 186 | 2.7 % |
| `current_vel` | 125 | 1.8 % |
| `active_queue` | 50 | 0.7 % |
| `motion_type` | 38 | 0.6 % |
| `current_line` | 12 | 0.2 % |
| `queue` | 12 | 0.2 % |
| `echo_serial_number` | 8 | 0.1 % |
| `exec_state` | 4 | 0.1 % |
| `command` | 2 | 0.0 % |
| `motion_mode` | 2 | 0.0 % |
| `task_mode` | 2 | 0.0 % |
| `inpos` | 2 | 0.0 % |
| `interp_state` | 2 | 0.0 % |
| `read_line` | 2 | 0.0 % |
| `state` | 2 | 0.0 % |
| `spindle` | 2 | 0.0 % |
| `file` | 1 | 0.0 % |

- never changed (61): `acceleration`, `adaptive_feed_enabled`, `ain`, `angular_units`, `aout`, `axis`, `axis_mask`, `block_delete`, `call_level`, `call_stack`, `cycle_time`, `debug`, `delay_left`, `din`, `dout`, `enabled`, `estop`, `feed_hold_enabled`, `feed_override_enabled`, `feedrate`, `flood`, `g5x_index`, `g5x_offset`, `g68_active`, `g68_offset`, `g68_rotation`, `g92_offset`, `homed`, `ini_filename`, `input_timeout`, `interpreter_errcode`, `joints`, `kinematics_type`, `limit`, `linear_units`, `max_acceleration`, `max_velocity`, `misc_error`, `mist`, `num_extrajoints`, `optional_stop`, `paused`, `pocket_prepped`, `probe_tripped`, `probe_val`, `probed_position`, `probing`, `program_units`, `queue_full`, `queued_mdi_commands`, `rapidrate`, `rotation_xy`, `single_stepping`, `spindles`, `task_paused`, `task_state`, `tool_from_pocket`, `tool_in_spindle`, `tool_offset`, `tool_table`, `velocity`

### gmoccapy_2_tools_with_cutter_radius_compensation_20ms.jsonl.gz

- ticks: 2146, duration 43.0 s, period 0.020 s (--period)
- file: 641735 bytes gzip; fields per tick: 91; LinuxCNC 2.10.0~pre2
- schema `emc_stat.schema.json`: 0 of 2146 ticks invalid
- standing still (current_vel == 0, inpos, previous tick also 0): 168 tick pairs; position fields changed anyway: none
- fields changing between consecutive ticks (count of 2145 pairs):

| field | changed | share |
|---|---:|---:|
| `heartbeat` | 2145 | 100.0 % |
| `taskbeat` | 2145 | 100.0 % |
| `actual_position` | 1923 | 89.7 % |
| `distance_to_go` | 1923 | 89.7 % |
| `dtg` | 1923 | 89.7 % |
| `joint` | 1923 | 89.7 % |
| `joint_actual_position` | 1923 | 89.7 % |
| `joint_position` | 1923 | 89.7 % |
| `position` | 1923 | 89.7 % |
| `current_vel` | 103 | 4.8 % |
| `motion_id` | 18 | 0.8 % |
| `motion_line` | 17 | 0.8 % |
| `gcodes` | 16 | 0.7 % |
| `mcodes` | 16 | 0.7 % |
| `settings` | 16 | 0.7 % |
| `motion_type` | 12 | 0.6 % |
| `echo_serial_number` | 8 | 0.4 % |
| `queue` | 7 | 0.3 % |
| `current_line` | 6 | 0.3 % |
| `command` | 4 | 0.2 % |
| `active_queue` | 4 | 0.2 % |
| `pocket_prepped` | 4 | 0.2 % |
| `read_line` | 4 | 0.2 % |
| `spindle` | 4 | 0.2 % |
| `interp_state` | 3 | 0.1 % |
| `tool_offset` | 3 | 0.1 % |
| `motion_mode` | 2 | 0.1 % |
| `task_mode` | 2 | 0.1 % |
| `exec_state` | 2 | 0.1 % |
| `inpos` | 2 | 0.1 % |
| `state` | 2 | 0.1 % |
| `tool_from_pocket` | 2 | 0.1 % |
| `tool_in_spindle` | 2 | 0.1 % |
| `tool_table` | 2 | 0.1 % |
| `flood` | 2 | 0.1 % |
| `mist` | 2 | 0.1 % |
| `file` | 1 | 0.0 % |

- never changed (54): `acceleration`, `adaptive_feed_enabled`, `ain`, `angular_units`, `aout`, `axis`, `axis_mask`, `block_delete`, `call_level`, `call_stack`, `cycle_time`, `debug`, `delay_left`, `din`, `dout`, `enabled`, `estop`, `feed_hold_enabled`, `feed_override_enabled`, `feedrate`, `g5x_index`, `g5x_offset`, `g68_active`, `g68_offset`, `g68_rotation`, `g92_offset`, `homed`, `ini_filename`, `input_timeout`, `interpreter_errcode`, `joints`, `kinematics_type`, `limit`, `linear_units`, `max_acceleration`, `max_velocity`, `misc_error`, `num_extrajoints`, `optional_stop`, `paused`, `probe_tripped`, `probe_val`, `probed_position`, `probing`, `program_units`, `queue_full`, `queued_mdi_commands`, `rapidrate`, `rotation_xy`, `single_stepping`, `spindles`, `task_paused`, `task_state`, `velocity`

