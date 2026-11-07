.importonce

// Integer coordinates approximate the golden ratio with 34/21. Importing this
// file emits no bytes; invoke IcosahedronModelData() after the BASIC entry point.
.const ICOSA_VERTEX_COUNT = 12
.const ICOSA_FACE_COUNT = 20
.const ICOSA_EDGE_COUNT = 30

.function IcosahedronTriple(a, b, c) {
    .var result = List()
    .eval result.add(a)
    .eval result.add(b)
    .eval result.add(c)
    .return result
}

.var icosaVertices = List()
.eval icosaVertices.add(IcosahedronTriple(  0, -21, -34))
.eval icosaVertices.add(IcosahedronTriple(  0, -21,  34))
.eval icosaVertices.add(IcosahedronTriple(  0,  21, -34))
.eval icosaVertices.add(IcosahedronTriple(  0,  21,  34))
.eval icosaVertices.add(IcosahedronTriple(-21, -34,   0))
.eval icosaVertices.add(IcosahedronTriple(-21,  34,   0))
.eval icosaVertices.add(IcosahedronTriple( 21, -34,   0))
.eval icosaVertices.add(IcosahedronTriple( 21,  34,   0))
.eval icosaVertices.add(IcosahedronTriple(-34,   0, -21))
.eval icosaVertices.add(IcosahedronTriple(-34,   0,  21))
.eval icosaVertices.add(IcosahedronTriple( 34,   0, -21))
.eval icosaVertices.add(IcosahedronTriple( 34,   0,  21))

.var icosaX = List()
.var icosaY = List()
.var icosaZ = List()
.for (var vertex = 0; vertex < ICOSA_VERTEX_COUNT; vertex++) {
    .eval icosaX.add(icosaVertices.get(vertex).get(0))
    .eval icosaY.add(icosaVertices.get(vertex).get(1))
    .eval icosaZ.add(icosaVertices.get(vertex).get(2))
}

// These are the twenty supporting triangles of the integer convex hull.
// Every winding points outward. Reversing screen Y makes a visible projected
// face have positive signed area, matching the existing culling routine.
.var icosaFaces = List()
.eval icosaFaces.add(IcosahedronTriple(0,  2, 10))
.eval icosaFaces.add(IcosahedronTriple(0,  4,  8))
.eval icosaFaces.add(IcosahedronTriple(0,  6,  4))
.eval icosaFaces.add(IcosahedronTriple(0,  8,  2))
.eval icosaFaces.add(IcosahedronTriple(0, 10,  6))
.eval icosaFaces.add(IcosahedronTriple(1,  3,  9))
.eval icosaFaces.add(IcosahedronTriple(1,  4,  6))
.eval icosaFaces.add(IcosahedronTriple(1,  6, 11))
.eval icosaFaces.add(IcosahedronTriple(1,  9,  4))
.eval icosaFaces.add(IcosahedronTriple(1, 11,  3))
.eval icosaFaces.add(IcosahedronTriple(2,  5,  7))
.eval icosaFaces.add(IcosahedronTriple(2,  7, 10))
.eval icosaFaces.add(IcosahedronTriple(2,  8,  5))
.eval icosaFaces.add(IcosahedronTriple(3,  5,  9))
.eval icosaFaces.add(IcosahedronTriple(3,  7,  5))
.eval icosaFaces.add(IcosahedronTriple(3, 11,  7))
.eval icosaFaces.add(IcosahedronTriple(4,  9,  8))
.eval icosaFaces.add(IcosahedronTriple(5,  8,  9))
.eval icosaFaces.add(IcosahedronTriple(6, 10, 11))
.eval icosaFaces.add(IcosahedronTriple(7, 11, 10))

// A proper coloring of the face-adjacency graph. Adjacent visible faces always
// have a nonzero XOR transition; zero remains the hidden/background color.
.var icosaFaceColors = List()
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(3)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(3)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(3)
.eval icosaFaceColors.add(2)
.eval icosaFaceColors.add(3)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(3)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(1)
.eval icosaFaceColors.add(3)

// Derive each undirected edge once, with its two adjacent face indices.
// Entries are [firstVertex, lastVertex, firstFace, lastFace].
.var icosaEdges = List()
.for (var first = 0; first < ICOSA_VERTEX_COUNT; first++) {
    .for (var last = first + 1; last < ICOSA_VERTEX_COUNT; last++) {
        .var adjacentFaces = List()
        .for (var face = 0; face < ICOSA_FACE_COUNT; face++) {
            .var hasFirst = false
            .var hasLast = false
            .for (var corner = 0; corner < 3; corner++) {
                .if (icosaFaces.get(face).get(corner) == first) { .eval hasFirst = true }
                .if (icosaFaces.get(face).get(corner) == last) { .eval hasLast = true }
            }
            .if (hasFirst && hasLast) { .eval adjacentFaces.add(face) }
        }
        .if (adjacentFaces.size() != 0) {
            .errorif adjacentFaces.size() != 2, "Icosahedron edge must join two faces"
            .var edge = List()
            .eval edge.add(first)
            .eval edge.add(last)
            .eval edge.add(adjacentFaces.get(0))
            .eval edge.add(adjacentFaces.get(1))
            .eval icosaEdges.add(edge)
            .errorif icosaFaceColors.get(adjacentFaces.get(0)) == icosaFaceColors.get(adjacentFaces.get(1)), "Icosahedron adjacent faces need different colors"
        }
    }
}
.errorif icosaEdges.size() != ICOSA_EDGE_COUNT, "Icosahedron must have thirty edges"
.errorif ICOSA_VERTEX_COUNT - icosaEdges.size() + icosaFaces.size() != 2, "Icosahedron Euler characteristic must be two"

// Optional runtime structure-of-arrays. Compile-time lists above also allow
// constant-address transforms, culling, and edge calls without indexed loops.
.macro IcosahedronModelData() {
@modelDataStart:
@modelX:          .fill ICOSA_VERTEX_COUNT, icosaX.get(i) & $ff
@modelY:          .fill ICOSA_VERTEX_COUNT, icosaY.get(i) & $ff
@modelZ:          .fill ICOSA_VERTEX_COUNT, icosaZ.get(i) & $ff
@modelFaceA:      .fill ICOSA_FACE_COUNT, icosaFaces.get(i).get(0)
@modelFaceB:      .fill ICOSA_FACE_COUNT, icosaFaces.get(i).get(1)
@modelFaceC:      .fill ICOSA_FACE_COUNT, icosaFaces.get(i).get(2)
@modelFaceColor:  .fill ICOSA_FACE_COUNT, icosaFaceColors.get(i)
@modelEdgeA:      .fill ICOSA_EDGE_COUNT, icosaEdges.get(i).get(0)
@modelEdgeB:      .fill ICOSA_EDGE_COUNT, icosaEdges.get(i).get(1)
@modelEdgeFaceA:  .fill ICOSA_EDGE_COUNT, icosaEdges.get(i).get(2)
@modelEdgeFaceB:  .fill ICOSA_EDGE_COUNT, icosaEdges.get(i).get(3)
@modelDataEnd:
}
