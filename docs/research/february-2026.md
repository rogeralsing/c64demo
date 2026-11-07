# The Hat and Aloft: author evidence and the remaining mechanism gap

Both releases are catalogued on CSDb as **1 February 2026**, at Fjälldata 2026. [The Hat](https://csdb.dk/release/?id=259070), by Fairlight and Genesis Project, credits **Alfatech and Trident** for code. [Aloft](https://csdb.dk/release/?id=259056), by Quiss and Genesis Project, credits **Quiss, Raistlin, Scrap and Sparta**, with Sparta also credited for the loader.

The targeted questions remain open: this bounded pass did **not** recover a creator-authored algorithm explanation or complete effect source for The Hat's final all-border upscroller, Aloft's three-layer moving pattern, or its bitmap Kefrens drawing. It did recover original artifacts, specific artist/coder statements and useful limits on the often-repeated descriptions. The source gap is a result of the routes inspected, not a claim that no explanation exists anywhere.

## Primary statements that can be supported

The Hat's artist **redcrab**, in his [23 March production note](https://csdb.dk/release/?id=259070&show=notes), links the [artwork collection](https://c64gfx.com/release/259070) and describes **500 frames of PETSCII animation available as GIFs**. That is an author statement about prepared artwork. This lane did not count every GIF frame or establish how the C64 packs, streams or draws them. It says nothing by itself about the final upscroller's hardware mechanism.

Aloft's [3 February artist notes by Mermaid](https://csdb.dk/release/?id=259056&show=notes) describe three differently lit cabin versions, scene layouts and intermediate artwork. She specifically says the big airplane was made from **18 sprites, two X-expanded**. This identifies an artwork construction; it does not establish 18 simultaneous hardware sprites, a multiplex schedule or the three-layer pattern's representation. The notes contain concrete process evidence rather than merely a finished screenshot, but their scope is the scenery and assets she describes.

Two [1 February coder notes](https://csdb.dk/release/?id=259056&show=hidden) establish intended interactions. **Sparta** says a joystick controls the movement of the flipped Kefrens bars on **side 2**. **Quiss** says the small Space Invaders game in the first hangar scene is playable. These support looking for original input consumers and state changes. Joystick control alone does not distinguish runtime geometry from prepared tables or selected animation states, and the hangar game is a separate feature.

Seven primary-note entries, including the four separate Mermaid notes, are preserved as structured text with their source pages in the receipt. No one is contacted and no input is injected in this pass.

## Comments that must not become author explanations

The lengthy Aloft review often returned by search is **Trident's 4 February comment**, not Quiss's technical write-up. Trident is a credited coder of The Hat, but is **not a credited coder of Aloft**. He explicitly says he still does not understand the three-layer moving pattern, even after Quiss explained it at the party. That confirms an interesting lead, not the contents of an explanation we possess.

Likewise, **HCL's 9 February Aloft comment** describes bitmap Kefrens updating every second line. It is an expert peer observation, not a native trace or a statement by its implementation author. Neither a double buffer, XOR/OR compositor, raster mode nor prepared-data format follows from that remark alone.

On The Hat, **Quiss's 2 February comment** says he looked at the all-border upscroll's code and jokingly calls it impossible. **Clarence** distinguishes the ending upscroller from a ghostbyte solution; **HCL** discusses recurring older sprite tricks elsewhere in the demo. These are peer reactions. They do not publish the instructions, prove historical priority, or justify applying the already studied [Trident ghostbyte teaching examples](ghostbyte-shine-through.md) to this ending. In particular, different parts of The Hat must not be collapsed into one assumed trick.

The receipt preserves these five selected comments with their actual authors and peer classifications. Search excerpts can misattribute neighboring comments, so the direct archived CSDb pages are the owning references.

## Public source routes inspected

Trident's linked public [`trident64/c64`](https://github.com/trident64/c64) repository still resolves to commit **`80d1027742815e55cda13a80cb4826744dd75c83`**, dated **11 February 2025**. Its complete non-truncated tree contains the anonymous IRQ/protothread example and the unexpanded-border-scroll teaching examples, not a published The Hat effect source. These are the sources already treated by the [macro-scheduling](macro-scheduling.md) and [ghostbyte](ghostbyte-shine-through.md) notes.

His separate [website repository](https://github.com/trident64/trident64.github.io) is newer: commit **`9c8bac3711136ca7d44b476bb8a962fa3bfab4d9`**, dated **16 March 2026**. Its complete tree, front page and feed were inspected. They did not yield the requested The Hat implementation. Selected text bytes are verified against the immutable Git trees; there is no substitution of the older teaching code for the released 2026 demo.

[Quiss's homepage](https://www.quiss.org/) has no Aloft reference in the acquired body. Its actual GitHub link identifies **`matthiaskramm`**, avoiding the unrelated account named `Quiss` that appears in broad searches. Complete first-page public-repository inventories were saved for that linked account, Trident, Sparta and Raistlin. No Aloft/The Hat source repository was recovered from them. This is an inventory-level negative result, not a recursive audit of every unrelated project or of private repositories. Raistlin's public-release repository's main branch is still the already pinned December 2025 source snapshot; his current article index yielded no Aloft mechanism post.

Two video leads are retained separately. [Martin Piper's end-scroller teardown](https://www.youtube.com/watch?v=Vfnyczaf1Ao) is titled *C64 Demos peek - The Hat - The end scroller part*. [FairLight TV #143](https://www.youtube.com/watch?v=tqX42YoncaA) is Trident's *No more raster time worrys* talk. Official YouTube metadata confirms those titles and uploader identities. **No transcript or frame-by-frame technical analysis was acquired here**, so neither video supplies a mechanism claim in this note. The latter title also does not turn the previously studied 2025 scheduling example into The Hat's effect source.

## A separate 2026 author technique was recovered

The website feed did lead to a substantive new-to-this-map source: Trident's **16 March 2026** [A Simple Technique for Overlapping IRQ Handlers](https://trident64.github.io/overlapping-irq-handlers/), including its complete Kickasm example. It links the Fjälldata 2026 talk. This is a general scheduling article, **not a recovered implementation of The Hat's upscroller or Aloft's effects**, and it makes no claim to have invented nested IRQs in 2026.

Its call/wait macro programs the next raster IRQ, tests a self-modified `running` immediate and skips the call if that expansion is already active. Otherwise it marks the flag, acknowledges the current VIC IRQ, executes `CLI` and calls the long subroutine. A later IRQ can interrupt that subroutine; stack-based A/X/Y preservation lets the older work resume when the nested handler returns. Completion clears the flag. The full example uses three colored workload routines to illustrate the ordering.

The guard is **per macro expansion/call site**; the shown code does not automatically exclude concurrent calls to the same routine from unrelated sites. Nesting also does not increase the machine's total cycle budget or make shared state safe. Stack use, other interrupt sources, routine state and publication deadlines still belong to the caller. These are limits of the visible code, not hardware tests performed here.

The article's **12-byte/19-cycle overhead figures remain author-reported**; no assembled-byte or timing-baseline check was made in this lane. The live article's complete example text matches the file at the pinned website commit, and is archived as `source/overlapping-irq-full-example.asm` inside the ignored output. This source/provenance equality establishes what was published, not that it was used by either demo or that its runtime timing is proven.

## Original artifacts, ready for a binary follow-up

Both ZIPs were acquired through the release's own download link. No executable or disk program was run.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [The Hat ZIP](https://csdb.dk/getinternalfile.php/276889/the_hat-flt%26gp.zip) | 522,048 | `ab15a74ba10a71264ccad74cd1d3a394b8f442a2acd33fd363b671bf293b081f` |
| Its `the-hat-7a825b1-a.d64` member | 174,848 | `ce09a1819a5dcec16342ebdc6515d20c377304db68e326ca2d86a499f0c9399d` |
| Its `the-hat-7a825b1-b.d64` member | 174,848 | `1527038ebebca1a3d3d3379b91dd1a77dffb6d6d89a4dbfc32bf3f6908eb5b21` |
| [Aloft ZIP](https://csdb.dk/getinternalfile.php/276871/Aloft.zip) | 419,712 | `275c0873b84dcea8ef03210506481f605e93f9f9b263bd5ce4c75dc39a7a1203` |
| Its `Aloft-Side2.d64` member | 174,848 | `a40374bc8b59ab13c06d577331dde5d3ccaef23ef5b434762d8ed9700b944d31` |

The Hat ZIP contains its two D64s and a cover JPEG; Aloft contains three D64s and four SID files. Every member hash is recorded. Neither ZIP has a separate assembly/source/text-note member. Their **disk internals were not decoded**, so that inventory does not rule out embedded notes or code inside the disks. The `7a825b1` string in The Hat filenames is retained as published, not asserted to identify an accessible source commit.

The strongest next binary case is **The Hat's final upscroller on the original side-B disk above**. First inventory its actual bootstrap/loader and locate the ending naturally from the original release; no entry PC or loader family is established here. Then bind the loaded code and font to that stage, identify its screen/bitmap/sprite consumers and pointer changes, and distinguish visible bitmap or character data from border-specific sprite data. Only source-bound instructions and later raster observations can decide what makes the all-border image, or whether a ghostbyte participates. No hypothetical implementation is promoted as the answer.

A second, specifically bounded Aloft case is the **side-2 flipped Kefrens interaction** described by Sparta. Recovering its input consumer would provide an author-linked way to select or vary the effect before investigating drawing code. It must remain separate from the three-layer pattern and the bitmap-Kefrens observation until original program boundaries are identified.

## Reproduction and limits

[february_sources.py](../../research/frontier-2026/february_sources.py) archives **28 successful direct routes**, including both release pages, notes/hidden-info pages, original ZIPs, official repository metadata and selected source/site text. Its offline checks validate response hashes, immutable Git blob bindings, archive member hashes, the structured attribution extracts and the live/pinned nested-IRQ example text. No arithmetic renderer or timing oracle is invented where original effect source was not recovered.

```sh
rtk proxy python3 research/frontier-2026/february_sources.py
```

`--fetch` acquires missing routes and preserves earlier changed bodies. Ignored output is under `build/research/frontier-2026/february-analysis/`, with final receipt `source-findings.json`. Passing here means acquisition/provenance checks pass; it does **not** mean the requested mechanisms have been solved. There was no CPU/native/process action, downloaded-host-code execution, source assembly, source-to-release byte match, image reconstruction, measured frame budget or established historical first.
