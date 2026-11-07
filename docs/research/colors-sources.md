# Colors: author-source search and attribution

Bounded search, 7 November 2026. **No published Colors source code or author explanation of its color-construction algorithm was located in the routes checked here.** That is a search result, not proof that none exists. Primary release/publication evidence was found; the detailed RGB/PAL descriptions encountered in release comments are viewer statements.

This lane only reads public text and the existing [release acquisition](../../build/research/colors/acquisition.json). It does not run the demo, interpret its CPU code, inspect a live emulator, or change the [main Colors note](colors.md). The [source receipt](../../build/research/colors/source-analysis/sources.json) records response hashes, failures, external links, comment attribution, and the official video linkage.

## Primary evidence found

The [CSDb release](https://csdb.dk/release/?id=262141) credits dev0, EGO, Schedar, and Strepto with code, and Vincenzo with music. Its preserved 36 comments contain **zero comments from those four coders**. The only commenter also listed among the release's participants is Vincenzo: his 7 June post reports replacing the ZIP's D64 files. It concerns the release version, not the rendering algorithm. The existing acquisition pins the current ZIP as `085301efa3282fddf8bfb64390ba90f50a7f3831e53f100f009f1cf4e2ee6383`; no equality to the initial party upload is assumed.

The four coder profiles—[dev0](https://csdb.dk/scener/?id=35906), [EGO](https://csdb.dk/scener/?id=19196), [Schedar](https://csdb.dk/scener/?id=34619), and [Strepto](https://csdb.dk/scener/?id=13717)—lead to the group website. None of those retrieved pages links a Colors repository. GitHub links in other inspected pages belong to general development tools or Pouët itself; they are not the demo's source.

The group's [HTTP website](http://lethargy.hu/) is accessible. Its home, [release list](http://lethargy.hu/releases), [members](http://lethargy.hu/members), and [social page](http://lethargy.hu/elerhetoseg) were preserved. The site's [Colors search](http://lethargy.hu/?s=Colors) returns “Nothing Found”. The HTTPS attempt failed certificate verification with a self-signed-certificate error; its exact failure is retained, and certificate checking was not disabled. This does not make the working HTTP route unavailable.

The [Lethargy Dev publication](https://medium.com/c64-dev) and [its feed](https://medium.com/feed/c64-dev) provide older development writing: **Unfortunate Coincidence**, **Behind the scenes: 5 Shades Of Grey**, and **C64 development today**. The retrieved feed has no Colors entry. These are useful primary explanations of other productions, not evidence that Colors uses the same implementation.

An actual group-owned publication chain was verified for the [linked Colors video](https://www.youtube.com/watch?v=9LWkHRAvNyA): the group's social page links channel `UCSTuJDwymX5wNolT2lK7OSg`, and the video's text metadata reports exactly that channel, **LethargyC64**. Its description gives the matching code/music credits and says the recording uses original C64 hardware. That is an uploader statement, not independently verified hardware provenance. It contains no construction explanation or source link. The exposed caption track is automatic Hindi speech recognition; it was not downloaded or treated as author technical text. No video/audio media was downloaded or watched in this lane.

## Viewer interpretations kept separate

The [release comments](https://csdb.dk/release/?id=262141#review) contain several leads, with different evidential status:

| Commenter | Date | What the statement supports |
|---|---|---|
| Copyfault | 6 November 2026 | Asks whether a write-up exists; proposes three consecutive RGB lines but explicitly leaves that interpretation uncertain. |
| ilesj | 18 June 2026 | Discusses PAL decoding, muted alternating RGB lines, and display/scaler differences. Not identified as a Colors author. |
| Photon | 8 June 2026 | Speculates that multiple converters were needed; supplies no code or author attribution. |

The retrieved [Pouët page](https://www.pouet.net/prod.php?which=106373) was added by Vincenzo and links that same group video. Its comments include requests for a write-up and reports about CRT appearance; no author algorithm explanation was located there. Viewer labels, brightness advice, the title, ranking, and video appearance do not establish a VIC mode, frame schedule, RGB-plane layout, converter pipeline, or attainable color count.

## Reproduction and limits

The [text acquisition/analysis script](../../research/colors/sources.py) has 16 explicit endpoints. Fifteen returned successful responses; the HTTPS group-site request is the recorded exception. Bodies and failure metadata remain under ignored `build/research/colors/source-analysis/`. It reuses the existing release page rather than overwriting the other lane's acquisition.

```sh
# Offline analysis of preserved responses:
python3 research/colors/sources.py

# Fetch newly listed routes while preserving earlier response receipts:
python3 research/colors/sources.py --fetch-missing
```

The [search ledger](../../build/research/colors/source-analysis/search-ledger.json) records representative web queries and their limited outcome. This pass did not authenticate to social networks, contact participants, enumerate private repositories, or claim exhaustive coverage of the web. A direct coder explanation or linked source archive would change the status; until then, the original binary/native lane must establish the actual mechanism independently.
