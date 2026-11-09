# Aloft: physical phi1 mapping of the glyph working set

Research date: 9 November 2026. **The physical mapping is now established for
both retained windows:** all forty low glyph addresses resolve to the same
addresses in main RAM. The two sets of 8,000 requests from the
[logical fetch binding](aloft-fetch-binding-20261109.md) therefore select
`mem_ram`, with no character-ROM, cartridge or CPU-port substitution.

This removes the earlier conditional bank0/RAM interpretation. It does not
by itself supply the time-varying byte returned by each request. The glyph
stream lane joins independently predicted stores and justified store/fetch
ordering to this mapping; final native RAM is not an input to that prediction.
Draw-pipeline/viewport work remains separate.

## The active memory implementation is C64SC

The pinned VICE 3.10 makefiles select `libc64sc`/`c64memsc.c` and `viciisc`
for `x64sc`. The fast emulator's `c64mem.c` bank-write behavior is not imported
into this proof. In the active path:

1. VIC powerup assigns `ram_base_phi1 = mem_ram`, address mask `$FFFF` and
   offset zero.
2. Plain C64SC memory initialization selects character-ROM mask `$7000` and
   match value `$1000`.
3. CIA2's effective port pins select the video bank through GLUE,
   `mem_set_vbank` and `vicii_set_vbank`; the latter shifts the bank number
   left fourteen bits for the phi1/phi2 offsets.
4. `fetch_phi1` translates the logical address, checks Ultimax/cartridge
   handling, checks the character-ROM predicate, and otherwise returns the
   byte at `ram_base_phi1 + translated_address`.

The resulting admitted tuple is:

```text
ram_base_phi1 = mem_ram
vbank_phi1   = $0000
address      = ((logical + $0000) & $FFFF) | $0000
chargen test = (address & $7000) == $1000
ultimax_phi1 = false
```

For every logical address `$0000..$07FF`, the translation is identity and the
character-ROM test is false. All 2,048 cases are enumerated. The actual
forty-address working set is a subset of that domain.

## Retained state and history bind the tuple

The [closed original-native custody](aloft-execution-native-20261109.md)
supplies eighteen version-checked snapshots, the exact startup argv, complete
monitor history and continuous watch generations. New narrow adapters read
the original source-defined module layouts; they do not modify the frozen
snapshot reader.

| Evidence | What it binds |
| --- | --- |
| `C64CART` v0.1 is the single byte `$00` in all eighteen snapshots | Its original writer records zero exported cartridges and immediately closes the module. |
| `C64MEMHACKS` v0.0 is `$00` in all eighteen snapshots | `MEMORY_HACK_NONE`, excluding the managed C64/+60K/+256K expansions. |
| `C64MEM` v0.1 has export EXROM/GAME zero | Matches the plain-machine export state. RAM contents are not used to infer this. |
| Both genuine initial CIA2 states have PRA `$08`, DDRA `$3C` | Effective pins `(PRA | ~DDRA)` have low bits `11`, selecting bank zero. |
| Both initial GLUE v1.0 payloads are `$01,$00,$00` | Old bank zero with no pending transition alarm. The source performs the bank switch before clearing an alarm. |
| Fresh `x64sc -default` original-D64 autostart; no restores/restarts or mapping-resource/cartridge commands | Excludes an earlier unrecorded expansion or cartridge setup within the owned case. |

The monitor command audit distinguishes monitor-bank selection from CPU/VIC
banking. Its fixed case contains no `resourceset`, cartridge attach/detach,
snapshot restore, reset or injected PC/RAM mutation. Attached watch commands
are exactly register queries. Neither the command history nor these snapshots
are treated as a generic guarantee about arbitrary emulator sessions.

A source-wide inventory checks 92 named mapping-API references, including
declarations/definitions and `mem_set_vbank`, and the direct assignments to
the relevant VIC mapping fields. Alternate address-mask paths belong to
other machine implementations excluded by the active build. Alternate RAM
bases in the C64 family belong to the disabled expansion paths. Active C64SC
bank selection goes through the inspected GLUE/memory path. The source
inventory is bounded reviewed evidence, not a general compiler call graph.

## The mapping remains stable through the final fetch

The source execution closure admits only the forty glyph/state locations and
`$D011` among cell data/I/O stores. The new consumer additionally checks
continuous native watches for CPU ports, `$D018` and CIA2 bank/DDRA from the
genuine dispatcher entry through each **after-line capture**. It checks the
complete hook stream for mapping writes through the final graphics request,
and finds none.

This closing boundary matters: `$F0B1` returns partway through the final
graphics line, before that line's remaining fetch slots. The mapping proof
does not stop its watch coverage at the chain return. Both after-line
captures lie beyond the final declared g-fetch clock, with no watch gap or
mapping change over the intervening tail.

The inherited source closure excludes unmodeled external NMI, reset/restore
or RAM-writing DMA and preserves the captured machine mapping. No claim is
extended to an uncontrolled external actor, another machine configuration or
an arbitrary future animation interval.

## CPU `$00/$01` and VIC RAM are different routes

The CPU's zero-page read function returns its port DDR/data for `$00/$01`.
The VIC phi1 fetch does not call that function: it indexes its RAM pointer
directly. Thus a logical VIC address zero or one selects underlying RAM,
without the CPU device overlay. The finite table explicitly includes these
two addresses; it does not mistake CPU port readbacks for RAM byte values.

The actual glyph requests all have address low bits `111`, so none addresses
the CPU ports. Their CPU writes take the ordinary zero-page RAM path or the
plain page-7 `ram_store` path, both updating the same `mem_ram` object seen
by phi1. The forty CPU glyph-store addresses therefore alias the resolved
VIC RAM bytes. This is an address/storage result, not a timing theorem.

In particular, C64SC's admitted RAM stores directly assign `mem_ram`; they
do not use the fast emulator's `vicii_write` catch-up wrapper. The separate
CPU-store clock audit and glyph stream establish when those changes become
visible relative to phi1 requests.

## Frozen resolver ABI and outputs

[physical_fetch.py](../../research/aloft-pixels-20261109/physical_fetch.py)
exports the pure function:

```text
resolve_phi1(logical_address, field["mapping"])
  -> {region: "mainRAM", physical_address: logical_address,
      cpu_port_overlay: false}
```

It accepts only the exact proved mapping tuple and `$0000..$07FF`; unknown
mapping variants fail closed. The [mapping ABI](../../build/research/aloft-pixels-20261109/physical-analysis/accepted-01/mapping-abi.json)
uses schema `aloft-c64sc-phi1-mainram-fields-v1` and a `fields` list keyed by
`label` (`first`, `later`). Each entry contains `mapping`, the inclusive
valid clock interval, genuine input/closing capture references, continuous
watch guards and the admitted CPU-store alias fact.

The separate physical-request export resolves both source-derived sets of
8,000 requests. It provides slot/clock/address records without returned byte
or pixel values. Consumers must use source-predicted glyph stores and their
independent timing bounds, rather than native final RAM, to supply data.

The [accepted receipt](../../build/research/aloft-pixels-20261109/physical-analysis/accepted-01/physical-fetch-proof.json)
is 3,221 bytes, SHA-256
`e4e815d4b793cbeb85c693ba6b963d5f0c3e41f7641ab5e36ec0c00a1d805678`.
The producer is 17,147 bytes,
`5dddabd2356cd93698528e14d51090cbc3518c74eee2891b03a8bdb9fefbd433`.
The ABI is 22,890 bytes,
`dbb18c657a4afb513187ab88a98365ffedf33f7f2a179919041f0ce92954f090`.

Fifteen retained source copies are checked byte for byte against the pinned
official VICE archive. Original source/decoder/custody artifacts remain
unchanged. Earlier candidates, a corrected source-range guard failure and
a local inspection syntax error remain documented in the new scope.

The [fresh self replay](../../build/research/aloft-pixels-20261109/physical-analysis/self-replay-check.json)
reproduces **six files / 3,705,723 bytes exactly**. No native/emulator, build,
CPU interpreter or downloaded host program is executed.
The independent [root source review and replay](../../build/research/aloft-pixels-20261109/physical-analysis/root-replay-check.json)
also reproduces all six files exactly after reviewing the active source
selection, mapping setters and state/history bounds. Its report is 1,175
bytes, SHA-256
`d081e949cfb35787e0af7a569d503ae338d24884d2630a2a527627a29602bdca`.

```sh
rtk proxy python3 -B research/aloft-pixels-20261109/physical_fetch.py \
  --output build/research/aloft-pixels-20261109/physical-analysis/new-replay
```

Continue with the clock-bounded predicted glyph-byte stream, then the
independent draw/pixel pipeline. Mapping is settled for these windows;
returned-data timing, committed viewport reconstruction, all-frame behavior
and the separately named scene retain their own proof requirements.
