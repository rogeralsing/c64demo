.importonce

// Two interpenetrating tetrahedra use the existing binary cube corners.
// Importing this module emits no bytes. Both front and back faces contribute
// to the XOR image; face selector zero is an uninked glass facet, not culling.
// Each tetrahedron uses all four selectors once. Equal contributions from
// the two bodies intentionally cancel into dark windows in their overlap.
.const GLENZ_VERTEX_COUNT = 8
.const GLENZ_FACE_COUNT = 8
.const GLENZ_EDGE_COUNT = 12
.label glenzHalfSize = HALF_SIZE
.errorif HALF_SIZE != 32, "Glenz requires thirty-two-unit cube corners"

.function GlenzTriple(a, b, c) {
    .var result = List()
    .eval result.add(a)
    .eval result.add(b)
    .eval result.add(c)
    .return result
}

.function GlenzParity(vertex) {
    .return (vertex & 1) ^ ((vertex >> 1) & 1) ^ ((vertex >> 2) & 1)
}

// Winding is outward for each independent tetrahedron. It remains useful for
// model validation even though this transparent experiment accepts both signs.
.var glenzFaces = List()
.eval glenzFaces.add(GlenzTriple(0, 3, 5))
.eval glenzFaces.add(GlenzTriple(0, 6, 3))
.eval glenzFaces.add(GlenzTriple(0, 5, 6))
.eval glenzFaces.add(GlenzTriple(3, 6, 5))
.eval glenzFaces.add(GlenzTriple(1, 4, 2))
.eval glenzFaces.add(GlenzTriple(1, 2, 7))
.eval glenzFaces.add(GlenzTriple(1, 7, 4))
.eval glenzFaces.add(GlenzTriple(2, 4, 7))

.var glenzFaceColors = List()
.eval glenzFaceColors.add(0)
.eval glenzFaceColors.add(1)
.eval glenzFaceColors.add(2)
.eval glenzFaceColors.add(3)
.eval glenzFaceColors.add(0)
.eval glenzFaceColors.add(2)
.eval glenzFaceColors.add(3)
.eval glenzFaceColors.add(1)

// Every edge lies within one parity class. The two classes are disconnected
// tetrahedra rather than the twelve axis-aligned edges of an ordinary cube.
.var glenzEdges = List()
.for (var face = 0; face < GLENZ_FACE_COUNT; face++) {
    .for (var corner = 0; corner < 3; corner++) {
        .errorif GlenzParity(glenzFaces.get(face).get(corner)) != floor(face/4), "Glenz face crosses tetrahedron components"
    }
}
.for (var first = 0; first < GLENZ_VERTEX_COUNT; first++) {
    .for (var last = first+1; last < GLENZ_VERTEX_COUNT; last++) {
        .var adjacentFaces = List()
        .for (var face = 0; face < GLENZ_FACE_COUNT; face++) {
            .var hasFirst = false
            .var hasLast = false
            .for (var corner = 0; corner < 3; corner++) {
                .if (glenzFaces.get(face).get(corner) == first) { .eval hasFirst = true }
                .if (glenzFaces.get(face).get(corner) == last) { .eval hasLast = true }
            }
            .if (hasFirst && hasLast) { .eval adjacentFaces.add(face) }
        }
        .if (adjacentFaces.size() != 0) {
            .errorif adjacentFaces.size() != 2, "Glenz edge must join two faces"
            .errorif GlenzParity(first) != GlenzParity(last), "Glenz edge joins separate tetrahedra"
            .errorif glenzFaceColors.get(adjacentFaces.get(0)) == glenzFaceColors.get(adjacentFaces.get(1)), "Glenz edge has a zero color transition"
            .var edge = List()
            .eval edge.add(first)
            .eval edge.add(last)
            .eval edge.add(adjacentFaces.get(0))
            .eval edge.add(adjacentFaces.get(1))
            .eval glenzEdges.add(edge)
        }
    }
}
.errorif glenzFaces.size() != GLENZ_FACE_COUNT || glenzEdges.size() != GLENZ_EDGE_COUNT, "Glenz must have eight faces and twelve edges"
.for (var component = 0; component < 2; component++) {
    .var edgeCount = 0
    .for (var edge = 0; edge < GLENZ_EDGE_COUNT; edge++) {
        .if (GlenzParity(glenzEdges.get(edge).get(0)) == component) { .eval edgeCount = edgeCount+1 }
    }
    .errorif edgeCount != 6 || 4-edgeCount+4 != 2, "Each Glenz tetrahedron must have six edges and Euler characteristic two"
}
.for (var vertex = 0; vertex < GLENZ_VERTEX_COUNT; vertex++) {
    .var degree = 0
    .for (var edge = 0; edge < GLENZ_EDGE_COUNT; edge++) {
        .if (glenzEdges.get(edge).get(0) == vertex || glenzEdges.get(edge).get(1) == vertex) { .eval degree = degree+1 }
    }
    .errorif degree != 3, "Each Glenz vertex must have three incident edges"
}

// Immutable structure-of-arrays for independent inspection of the assembled
// model. Drawing below uses the compile-time lists and constant addresses.
.macro GlenzModelData() {
@glenzTablesStart:
@glenzFaceA:      .fill GLENZ_FACE_COUNT, glenzFaces.get(i).get(0)
@glenzFaceB:      .fill GLENZ_FACE_COUNT, glenzFaces.get(i).get(1)
@glenzFaceC:      .fill GLENZ_FACE_COUNT, glenzFaces.get(i).get(2)
@glenzFaceColor:  .fill GLENZ_FACE_COUNT, glenzFaceColors.get(i)
@glenzEdgeA:      .fill GLENZ_EDGE_COUNT, glenzEdges.get(i).get(0)
@glenzEdgeB:      .fill GLENZ_EDGE_COUNT, glenzEdges.get(i).get(1)
@glenzEdgeFaceA:  .fill GLENZ_EDGE_COUNT, glenzEdges.get(i).get(2)
@glenzEdgeFaceB:  .fill GLENZ_EDGE_COUNT, glenzEdges.get(i).get(3)
@glenzTablesEnd:
    .assert "Glenz model table bytes", glenzTablesEnd-glenzTablesStart, GLENZ_FACE_COUNT*4+GLENZ_EDGE_COUNT*4
}

// Full-image drawing contract: all eight face selectors participate, with no
// orientation rejection. Per-edge XOR transitions combine their contributions
// before the unchanged exact boundary sampler and single prefix fill.
.macro GlenzDrawCode() {
@glenzDrawCodeStart:
    .for (var face = 0; face < GLENZ_FACE_COUNT; face++) {
        lda #glenzFaceColors.get(face)
        sta xorFaceColors+face
    }
    .for (var edge = GLENZ_EDGE_COUNT-1; edge >= 0; edge--) {
        .var first = glenzEdges.get(edge).get(0)
        .var last = glenzEdges.get(edge).get(1)
        .var firstFace = glenzEdges.get(edge).get(2)
        .var lastFace = glenzEdges.get(edge).get(3)
        lda #(glenzFaceColors.get(firstFace) ^ glenzFaceColors.get(lastFace))
        sta boundaryColor
        lda projectedX+first
        sta lineX0
        lda projectedY+first
        sta lineY0
        lda projectedX+last
        sta lineX1
        lda projectedY+last
        sta lineY1
        jsr drawBoundary
    }
    rts
@glenzDrawCodeEnd:
}
