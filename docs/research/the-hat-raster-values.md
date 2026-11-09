# The Hat upscroll: typed raster-value prediction

Status: **in progress; no native acceptance receipt yet**. The new consumer
is deliberately fail-closed until the closed native03 custody proof and its
live raster-read inputs are pinned. Existing research artifacts are unchanged.

The [consumer](../../research/the-hat/raster_values.py) uses the complete
[source macros](the-hat-raster-source.md), rather than executing 6502 opcodes.
Each guarded macro is lowered into its individual semantic stages at the
original PCs: a load, binary addition, optional CLC and each store remain
separate stages. This permits a cutoff between arithmetic and a later
store, including inside an interleaved coordinate/border write train.
Static lowering currently covers all 6,521 nonselector instruction sites;
the four selector instructions choose the branch through pointer bit 3.
That check is source coverage, not native write agreement.

Prediction inputs are the entry RAM and logical VIC registers, CPU decimal
flag clear and CPU-port low bits `$05` (HIRAM clear for the RAM tables/code,
with I/O mapped), current table generation, exact shared helper
bytes, ordered independently observed `LDY $D012/$D112` values, and the
stacked cutoff PC. Expected native stores, write counts and ending register
values are excluded from the prediction API. The source graph determines
loop targets; the live read sequence disambiguates repeated visits to a
cutoff PC. Only when all supplied reads have been consumed may that PC stop
the last partial iteration. No CPU clock or IRQ timing is synthesized.

The frozen hardware layer supplies software-visible VIC reads and logical
register stores. INC/DEC update a byte modulo 256 while preserving CPU
carry; D016 reads include its forced high bits. Physical NMOS dummy writes,
VIC pipelines, DMA and pixels remain separate. Raw CPU store bytes and
logical stored-register bytes are retained as different quantities.

The planned checks distinguish the available oracles. Instruction hooks
bind write PC/address/order. Post CPU A/X/Y independently bind ordinary
STA/STX/STY/SAX bytes. RMW hooks without I/O queries expose only operation,
address and N/Z; they do not directly record every intermediate data byte.
Additional readback windows can test software-visible post-RMW register
values, while cutoff snapshots supply complete final stored bytes. Those
observation classes must not be combined into an invented data-bus trace.

The root-owned native case is still live. This note will record exact
accepted inputs, comparisons, failure controls and replay results after
custody is closed and the value producer has actually passed.
