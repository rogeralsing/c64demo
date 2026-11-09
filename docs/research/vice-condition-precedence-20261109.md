# VICE 3.10: an accepted guard can still be always false

The previously unexplained missed Aloft SYS breakpoint now has a concrete cause: **VICE evaluates condition operators at one left-associative precedence**. The old unparenthesized byte predicate cannot become true. This is a monitor-command error, not evidence of a C64 bootstrap or renderer failure. Older frozen observations remain unchanged; this note supplies the later correction and evidence.

The exact old command was:

```text
break exec $0810 if @ram:$0810 == $a9 && @ram:$0811 == $ff
```

Its actual parse is:

```text
((RAM[$0810] == $A9) && RAM[$0811]) == $FF
```

C logical AND produces integer zero or one. Comparing that result with `$FF` (255) is always false. No assumption about which bytes the older machine had at SYS is needed for this conclusion.

Use explicit comparison grouping:

```text
break 0810 if (@ram:$0810 == $a9) && (@ram:$0811 == $ff)
```

The general operational rule is to group each comparison when joining monitor predicates with `&&` or `||`. A short unconditional checkpoint followed by host-side byte validation is another useful observation method. A successful setup response proves syntax acceptance; it does not prove the predicate's intended meaning.

## Primary-source derivation

The retained official VICE 3.10 archive is pinned at SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`. The passive [condition producer](../../research/aloft-decode-20261109/condition.py) reads three exact members as data and verifies their retained copies against the archive:

- `src/monitor/mon_lex.l` maps both equality and logical AND to the same `COND_OP` token.
- `src/monitor/mon_parse.y` declares that token left-associative and builds one common binary `cond_expr` production. Explicit parentheses preserve grouped subtrees. The source comment confirms the shared precedence.
- `src/monitor/monitor.c` evaluates equality and logical AND as C expressions. Its RAM condition read returns an unsigned byte.

The producer models only these two exact predicates. It exhausts **all 65,536 unsigned-byte pairs**: the old expression has **zero** true pairs; the grouped expression has exactly one, `$A9/$FF`. Python's value-returning `and` is not substituted for C logical AND: the model explicitly converts both operands to Boolean and the intermediate result to integer0/1.

This is a finite condition-algebra proof, not a general monitor parser, CPU interpreter or arbitrary-expression theorem. No original C/C++ source is compiled or executed.

## Independent fresh native witness

The [fresh original startup case](aloft-stream-native-20261109.md) reaches SYS `$0810` with an unconditional checkpoint and verifies all 830 original bootstrap bytes. It later pauses at first receive `$019F`. The original `$0810/$0811` bytes remain `$A9/$FF` before depacking.

Root creates two short checkpoints at the next source-bound packet entry `$021C`: checkpoint6 uses the exact old ungrouped predicate; checkpoint7 uses grouped comparisons. Both successful setup responses are inspected before execution, and the unconditional packet checkpoint is disabled. The natural run stops on **checkpoint7 at clock 9,380,860**, with the expected byte pair still present. Checkpoint6 is absent from that stop response. The source proof explains its always-false result independently of checkpoint processing order.

The witness uses another PC against the same original byte predicate. It does not replay or alter the older case. Full boot, wire, checkpoint and RAM/VSF custody belongs to the separate native proof; this producer consumes its pinned records only after closure.

## Acceptance and continuation

The [accepted condition proof](../../build/research/aloft-decode-20261109/condition-analysis/accepted-01/condition-proof.json) is 7,953 bytes, SHA-256 `2121a47b1e37d38058489effc80916a092b6147af6d20695593bfc8ae6555e8f`. The producer is 9,089 bytes, SHA-256 `9490339583392d44cfc76f7fc1dbdc532f33dcbb48d7f39f76008638ca1df64a`.

Independent peer review found no material issue; a fresh replay reproduced **all three outputs / 20,398 bytes** exactly. The [peer report](../../build/research/aloft-decode-20261109/condition-analysis/peer-replay-check.json) is 1,634 bytes, SHA-256 `d5747531be8beb8ca74d344425ae38deb7eeafa12c3ab71dc056cee63206e258`.

```sh
rtk proxy python3 -B research/aloft-decode-20261109/condition.py --output build/research/aloft-decode-20261109/condition-analysis/replay-NEW
```

Use grouped predicates in future research. Preserve the old failed command, wait/interruption and later correction as separate evidence. This finding changes no product, viewer, exporter, original demo, earlier artifact or earlier receipt.
