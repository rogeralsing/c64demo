#!/usr/bin/env python3
"""Pin and inspect VICE 3.10's x64sc monitor timing path; no execution.

This extracts official archived source, checks specific textual structures,
and records line references. It does not build or run VICE, a CPU or a trace.
"""

import hashlib
import json
import re
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
OUTPUT = ROOT / "build/research/vice-trace-timing"
ARCHIVE_SHA256 = "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1"
MEMBERS = [
    "src/c64/c64cpusc.c", "src/mainc64cpu.c", "src/6510dtvcore.c",
    "src/c64/c64memsc.c", "src/c64/c64.c", "src/monitor/monitor.c",
    "src/monitor/mon_breakpoint.c", "src/monitor/mon_disassemble.c",
    "src/monitor/mon_register6502.c", "src/viciisc/vicii-mem.c",
    "src/c64/c64-snapshot.c",
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    assert digest(ARCHIVE.read_bytes()) == ARCHIVE_SHA256
    OUTPUT.mkdir(parents=True, exist_ok=True)
    sources, files = {}, []
    with tarfile.open(ARCHIVE) as archive:
        for member in MEMBERS:
            raw = archive.extractfile("vice-3.10/" + member).read()
            path = OUTPUT / "source" / member
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
            sources[member] = raw.decode()
            files.append({"member": "vice-3.10/" + member, "bytes": len(raw), "sha256": digest(raw),
                          "path": str(path.relative_to(ROOT))})
    sc, maincpu, core = (sources[name] for name in MEMBERS[:3])
    mem, machine, monitor, checkpoint, disasm = (sources[name] for name in MEMBERS[3:8])
    interrupt_macro = core[core.index("#define DO_INTERRUPT(int_kind)"):core.index("/* Addressing modes.")]
    undump = monitor[monitor.index("int mon_read_snapshot("):monitor.index("/* *** WATCHPOINTS *** */")]
    cpu_snapshots = maincpu[maincpu.index("int maincpu_snapshot_write_module("):]
    c64_snapshot_read = sources["src/c64/c64-snapshot.c"][sources["src/c64/c64-snapshot.c"].index("int c64_snapshot_read("):]
    checks = {
        "x64sc_includes_shared_main_cpu": '#include "../mainc64cpu.c"' in sc,
        "shared_main_uses_6510dtvcore": '#include "6510dtvcore.c"' in maincpu,
        "clock_increment_advances_cpu_then_vic": re.search(r"maincpu_clk\+\+;.*?vicii_cycle\(\)", sc, re.S) is not None,
        "sta_abs_calls_set_abs": re.search(r"case 0x8d:.*?ST\(reg_a_read, SET_ABS, 3\)", core, re.S) is not None,
        "set_abs_store_then_clock": re.search(r"#define SET_ABS\(value\).*?STORE\(p2, value\);.*?CLK_INC\(\);", core, re.S) is not None,
        "rmw_dummy_then_clock_then_final_then_clock": re.search(r"#define SET_ABS_RMW\(old_value, new_value\).*?STORE_DUMMY\(p2, old_value\);.*?CLK_INC\(\);.*?STORE\(p2, new_value\);.*?CLK_INC\(\);", core, re.S) is not None,
        "x64sc_performs_dummy_cycles": "#define SKIP_CYCLE 0" in sc,
        "watch_hook_queues_before_memory_handler": re.search(r"static void store_watch\(.*?monitor_watch_push_store_addr\(addr, e_comp_space\);.*?mem_write_tab\[mem_config\]\[addr >> 8\]\(addr, value\);", mem, re.S) is not None,
        "queued_store_contains_address_not_clock_or_value": "static uint16_t watch_store_array[MONITOR_MAX_CHECKPOINTS + 1][NUM_MEMSPACES];" in monitor,
        "enqueue_retains_duplicates": "watch_store_array[watch_store_count[mem]][mem] = addr;\n    watch_store_count[mem]++;" in monitor,
        "boundary_watch_check_uses_last_opcode_address": "monitor_check_watchpoints(LAST_OPCODE_ADDR, (uint16_t)reg_pc);" in core,
        "last_address_is_set_before_fetch": core.index("SET_LAST_ADDR(reg_pc);") < core.index("FETCH_OPCODE(opcode);"),
        "store_disassembly_uses_lastpc": "loadstorepc = new_addr(mem, lastpc);" in checkpoint and "mon_disassemble_with_regdump(mem, loadstorepc);" in checkpoint,
        "checkpoint_raster_is_sampled_when_printed": "mon_interfaces[mem]->get_line_cycle(&line, &cycle, &half_cycle);" in checkpoint,
        "machine_raster_comes_from_current_clock": "((maincpu_clk) % machine_timing.cycles_per_line)" in machine,
        "stopwatch_is_current_clock_minus_base": "(*vice_interface->clk - stopwatch_start_time[default_memspace])" in monitor,
        "dummy_default_is_off": "int break_on_dummy_access = 0;" in monitor,
        "dummy_watch_tables_selected_only_when_enabled": "if (flag > 1)" in mem and "_mem_write_tab_ptr_dummy = mem_write_tab_watch;" in mem and "_mem_write_tab_ptr_dummy = mem_write_tab[mem_config];" in mem,
        "watch_wrapper_ignores_monitor_generated_accesses": re.search(r"void monitor_watch_push_store_addr.*?if \(inside_monitor\).*?return;", monitor, re.S) is not None,
        "exec_checkpoint_stops_before_store_queue_drain": interrupt_macro.index("if (monitor_mask[CALLER] & (MI_BREAK))") < interrupt_macro.index("if (monitor_mask[CALLER] & (MI_WATCH))") and "monitor_startup(CALLER);" in interrupt_macro,
        "monitor_boundary_precedes_next_instruction_fetch": core.index("DO_INTERRUPT(pending_interrupt);") < core.index("SET_LAST_ADDR(reg_pc);") < core.index("FETCH_OPCODE(opcode);"),
        "undump_wrapper_does_not_clear_watch_queue": "machine_read_snapshot(name, even_mode)" in undump and "watch_store" not in undump and "monitor_init" not in undump,
        "c64_snapshot_restore_has_no_monitor_module_or_reinit": "maincpu_snapshot_read_module(s)" in c64_snapshot_read and "monitor_" not in c64_snapshot_read,
        "cpu_snapshot_omits_last_opcode_addr": "last_opcode_info" in cpu_snapshots and "last_opcode_addr" not in cpu_snapshots,
        "store_queue_counts_reset_only_at_init_or_drain": re.findall(r"watch_store_count\[[^]]+\]\s*=\s*0", monitor) == ["watch_store_count[i] = 0", "watch_store_count[mem] = 0"],
    }
    assert all(checks.values()), {key: value for key, value in checks.items() if not value}
    anchors = [
        ("src/c64/c64cpusc.c", "#define CLK_INC()", 8, "CPU/VIC clock increment order"),
        ("src/c64/c64cpusc.c", "#define SKIP_CYCLE 0", 1, "x64sc retains dummy cycles"),
        ("src/mainc64cpu.c", '#include "6510dtvcore.c"', 1, "actual x64sc core include"),
        ("src/6510dtvcore.c", "#define SET_ABS(value)", 12, "normal and RMW store clock order"),
        ("src/6510dtvcore.c", "#define DEC(pc_inc", 10, "DEC new value and PC before writes"),
        ("src/6510dtvcore.c", "#define INC(pc_inc", 10, "INC new value and PC before writes"),
        ("src/6510dtvcore.c", "#define ST(value", 5, "STA PC advances before store"),
        ("src/6510dtvcore.c", "monitor_check_watchpoints(LAST_OPCODE_ADDR", 3, "deferred watchpoint drain"),
        ("src/6510dtvcore.c", "if (monitor_mask[CALLER] & (MI_BREAK))", 16, "exec breakpoint stops before queued store traces drain"),
        ("src/6510dtvcore.c", "SET_LAST_ADDR(reg_pc);", 26, "record instruction owner before fetching"),
        ("src/c64/c64memsc.c", "static void store_watch", 7, "address enqueue then actual write"),
        ("src/c64/c64memsc.c", "static void mem_update_tab_ptrs", 24, "dummy on/off handler selection"),
        ("src/monitor/monitor.c", "int break_on_dummy_access = 0;", 1, "default dummy setting"),
        ("src/monitor/monitor.c", "void monitor_watch_push_store_addr", 15, "address-only queue, no deduplication"),
        ("src/monitor/monitor.c", "static bool watchpoints_check_stores", 21, "print each queued address at boundary"),
        ("src/monitor/mon_breakpoint.c", "loadstorepc = new_addr(mem, lastpc);", 1, "store instruction PC comes from lastpc"),
        ("src/monitor/mon_breakpoint.c", "mon_interfaces[mem]->get_line_cycle(&line", 15, "trace raster obtained at print time"),
        ("src/monitor/mon_breakpoint.c", "mon_disassemble_with_regdump(mem, loadstorepc);", 5, "store trace uses owner PC"),
        ("src/monitor/monitor.c", "void mon_stopwatch_show", 11, "printed cycle number can be relative"),
        ("src/c64/c64.c", "void machine_get_line_cycle", 7, "raster computed from current main clock"),
        ("src/monitor/mon_disassemble.c", "void mon_disassemble_with_regdump", 19, "instruction and current register/clock formatting"),
        ("src/monitor/monitor.c", "watch_load_occurred = false;", 10, "monitor_init resets debugger queues"),
        ("src/monitor/monitor.c", "int mon_read_snapshot(", 12, "undump wrapper does not clear queues"),
        ("src/mainc64cpu.c", "int maincpu_snapshot_write_module(", 40, "MAINCPU snapshot saves last_opcode_info, not owner address"),
        ("src/mainc64cpu.c", "int maincpu_snapshot_read_module(", 67, "MAINCPU restores machine state without owner address"),
        ("src/c64/c64-snapshot.c", "int c64_snapshot_read(", 50, "C64 snapshot restores machine modules without monitor queues"),
    ]
    references = []
    for path, needle, count, meaning in anchors:
        lines = sources[path].splitlines()
        index = next(i for i, line in enumerate(lines) if needle in line)
        excerpt = "\n".join(lines[index:index + count]) + "\n"
        references.append({"file": path, "start_line": index + 1, "end_line": index + count,
                           "meaning": meaning, "excerpt_sha256": digest(excerpt.encode())})
    sample_start, sample_trace = 259896790, 259896794
    example = {"provenance": "Measurement supplied by parent; not reproduced or reread by this source-only script",
               "opcode_pc": 0x7024, "pre_instruction_clock": sample_start,
               "reported_trace_clock": sample_trace, "clock_difference": sample_trace - sample_start,
               "pre_pal_line_cycle": [sample_start // 63 % 312, sample_start % 63],
               "trace_pal_line_cycle": [sample_trace // 63 % 312, sample_trace % 63],
               "normal_store_callback_clock": sample_trace - 1,
               "normal_store_callback_pal_line_cycle": [(sample_trace - 1) // 63 % 312, (sample_trace - 1) % 63],
               "condition": "Normal STA path with no clock-advancing interrupt/trap/alarm handling between store and checkpoint printing; monitor stopwatch base must be accounted for"}
    rmw_endpoint = {"provenance": "Additional native facts supplied by parent; not reproduced or reread here",
                    "dec_opcode_pc": 0x6763, "inc_opcode_pc": 0x6766, "following_rts_pc": 0x6769,
                    "pre_dec_clock": 265812191, "pre_rts_clock": 265812243,
                    "dec_dummy_on_records": 2, "dec_trace_clock": 265812197,
                    "inc_records_before_exec_stop": 0,
                    "source_interpretation": "Exec checkpoint at6769 can enter the monitor before MI_WATCH drains stores queued by INC6766; absence at this stopped endpoint is not an access absence",
                    "required_capture_boundary": "Resume with trace preserved, or stop beyond the next queue drain; parent selected original RTS return631B",
                    "later_supplied_observation": "First extended run printed six records: two DEC-labelled records at the restored pre-instruction clock, then two DEC and two INC records at their later boundaries. Source proves queue persistence is possible across undump, but does not independently prove ownership of those two early records.",
                    "clean_return_run_supplied_by_parent": {"dec_records": 2, "dec_owner_pc": 0x6763,
                        "dec_report_clock": 265812197, "inc_records": 2, "inc_owner_pc": 0x6766,
                        "inc_report_clock": 265812243, "return_pc": 0x631B,
                        "return_clock": 265812249, "return_pal_line_cycle": [66, 3],
                        "capture_prefix": "selector-rmw-clean-return-after-", "independently_reread_or_reproduced": False}}
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "archive": str(ARCHIVE.relative_to(ROOT)), "archive_sha256": ARCHIVE_SHA256,
              "source_files": files, "checks": checks, "references": references, "example": example,
              "supplied_rmw_endpoint": rmw_endpoint,
              "scope": "Pinned source inspection only; no emulator, CPU, trace, compiler, native process or timing experiment executed"}
    (OUTPUT / "source-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "source_files": len(files), "structural_checks": len(checks),
                      "line_references": len(references), "example": example}, indent=2))


if __name__ == "__main__":
    main()
