# Cancellable owned VICE observations

The new [live observer](../../research/vice_session_live.py) keeps stdin active
while a monitor command waits. It starts one owned PAL VICE process, uses one
socket reader, and serializes ordinary monitor commands. It does not replace
the frozen [earlier helper](../../research/vice_session.py), whose SHA-256 remains
`173134636447e1c670074c49dc3007751390958ce39990036568c6cbe5826124`.

The Dragonbond `native-02` optional main-loop/raster observation did not return.
The wrapper was interrupted before its cleanup ran, so separate owner cleanup
had to identify and terminate the orphaned VICE process. The
[native lineage note](dragonbond-native.md) preserves that failure and its
actual closure. This observer addresses cancellation and evidence retention;
it does not invent the missing observation or alter the old receipts.

## Start and command interface

Use a new output directory. An existing directory is rejected before launch.
The launch flags and program/disk arguments match the earlier helper.

```sh
rtk proxy python3 research/vice_session_live.py original.d64 \
  --disk original.d64 --no-autostart \
  --output build/research/example/native-live-01
```

The observer first requests registers and `sidefx off`, then emits `ready`.
Each subsequent input line is a JSON object:

```json
{"command":"break 2808 if RL == $10b","id":"optional-break"}
{"command":"x","id":"optional-observation"}
{"interrupt":true}
{"command":"r","id":"after-interrupt"}
{"close":true}
```

Commands receive an internal sequence number and optional caller `id`.
An accepted ordinary command waits in order; it is not sent while another
response is pending. Completed responses include their command, status and
received-byte offsets. Monitor input remains explicit: callers must still
audit their commands and distinguish restores, data writes and execution.

`interrupt` is available while `x` or `exit` is pending. It sends the read-only
register command `r` on the **same connection**. A second interrupt does not
send another command. An interrupt outside a pending resume is rejected.
The pending-interrupt marker is installed only after that input is fully sent.
A failed send is recorded and ends the owned session, because partial monitor
input cannot safely be retried.

The observer waits for a `.;` register row from the interrupt response and a
trailing monitor prompt before releasing the ordinary queue. A natural
breakpoint prompt racing with the interrupt cannot satisfy that condition
alone. Both the earlier prompt and final register response remain in the
interrupted response. Its status is `interrupted`, not proof that the original
breakpoint condition completed. No stale prompt is assigned to the next
ordinary command.

After `--observation-timeout` seconds, default 30, the observer emits one
`partial`/`waiting` notice. It keeps the same command, connection and process
pending. It never retries, restores, advances PC or starts a replacement
session after a timeout. Send `interrupt` or `close` to end the wait.

## Close and evidence

`close`, stdin EOF, SIGINT and SIGTERM request controlled closure. Unsent
commands are cancelled and recorded. A pending resume receives the same
read-only interrupt; the observer allows `--close-grace` seconds, default 3,
to consume registers and the prompt. A non-resume command may finish during
that grace period. Remaining response bytes are retained as partial.

The observer then terminates and waits for **its own `Popen` child only**.
It escalates to kill only if that child does not terminate within five
seconds. `session.json` records the actual exit code, reaped state, closure
time and any observer error. No external process scan, broad kill or emulator
restart occurs. A hard host kill or power loss can still prevent cleanup;
an absent closure record must not be interpreted as successful closure.

Evidence is flushed incrementally:

- `input.bin`: exact stdin bytes, including incomplete or rejected JSON.
- `sent.bin`: exact bytes successfully sent to the monitor.
- `received.bin`: exact bytes received, including output before a prompt.
- `events.jsonl`: input history, byte ranges, queued/sent/cancelled commands,
  interrupt boundaries, completed/partial responses and lifecycle records.
- `monitor.log`: a readable interleaving of sent commands and received output.
- `vice.log`: output from the owned emulator; `session.json`: process identity
  and actual closure, written through an atomic replacement.

The binary streams and event offsets are authoritative. An interrupt can
interleave input with a pending command's response, so the readable log must
not be fed to the frozen sequential transcript parser without adapting its
ownership rules. Incremental flushes preserve bytes already observed if a
later observation stalls; they do not claim crash-proof disk durability.

## Retained real verification

Two successful closed VICE sessions now exercise the actual JSON and monitor
wire interface. The passive [contract verifier](../../research/verify_vice_live.py)
reads their retained evidence without starting an emulator, process, CPU model
or live connection:

```sh
rtk proxy python3 research/verify_vice_live.py
```

The result is
[verification.json](../../build/research/vice-live-verification/verification/verification.json).
Its source and capture hashes pin the actual producer, frozen sequential
helper, rejected producer, three sessions, raw wire files and event histories.
For every session, event ranges cover all exact input/sent/received bytes.
Sent groups reconstruct monitor command bytes; completed and partial response
ownership reconstructs the corresponding raw received ranges. Ordinary
commands serialize, with no retry or process restart after a waiting notice.

`interrupt-02` checks a pending `x` interrupted by `r` on the existing
connection. The queued ordinary `r` returns identical PC, registers, ports,
flags, raster position and clock. An any-PC raster-267 checkpoint then stops
naturally; its next `r` agrees with all visible stop-state fields. A later
pending-close request cancels the queued `cancel-on-close` command before it
reaches the wire, drains the interrupt's register response and prompt, then
reaps the owned VICE process with recorded exit code −15.

`trace-01` preserves **4,711,018 raw received bytes before a completed response**
in a separate pending-prefix artifact. Those bytes include actual `FD75`
instruction-trace output. The verifier checks the saved pending observation,
its waiting notice, and exact equality with the final received stream's
prefix. A later read-only interrupt drains registers and the prompt; close
reaps that owned process with exit code −15. The trace was not continuous at
cancellation, so this case does not claim continuous tracing through the
interrupt instant.

The first live interrupt check exposed a duplicate `utc` keyword in the event
journal call. No interrupt command reached the wire in that run. The failed
producer and evidence remain under
`build/research/vice-live-verification/rejected-utc-collision/` and the closed
`interrupt-01/` session. Interrupt metadata now uses `requested_utc`, and a
programming `TypeError` is no longer treated as rejected user input. Replacement
verification must use a new directory; the failed session is not overwritten.

The verifier demonstrably rejects that retained pre-fix interruption because
no interrupt `r` reached the original wire, while accepting the fixed cases.
The failed session's eventual owned cleanup is checked separately from the
failed cancellation contract. No helper-process exit value is inferred from
the owned VICE exit code.

This verification protects observable JSON/wire ordering, cancellation and
process ownership. The credible regression is the retained UTC collision,
which left `x` pending without sending `r`. Sequential snapshot audits cannot
exercise stdin while `x` waits or prove incremental wire persistence. The
checks use the actual public interface and require no production test seam,
mock monitor or second implementation of the observer's private state machine.

The retained natural-stop and interrupt cases are separate. They do not force
a simultaneous stop/interrupt race. Register agreement is not full RAM/device
state agreement. These reset-machine monitor checks establish no Dragonbond
artwork, physical-hardware, complete-run timing, forced send-failure or
power-loss-durability result. A later native investigation keeps its own
capture lineage and permitted-command audit.
