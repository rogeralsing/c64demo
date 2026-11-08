"""Independent MUI file-address/pixel decoder; no serializer packing tables.

Physical address arithmetic follows the VIC screen pages, sprite pointers and
counter wraps, independently of Mufflon's muifli_scram/muifli_spram arrays.
This decoder is deliberately separate from the art generator and serializer.
"""


def memory_image(data):
    if len(data) != 0xAC02 or data[:2] != b"\x00\x21":
        raise ValueError("Expected uncompressed Mufflon MUIFLI load$2100/size$AC00")
    memory = bytearray(65536)
    memory[0x2100:0xCD00] = data[2:]
    memory[0xCD00:0xF700] = memory[0x7700:0xA100]
    for bank in (0, 0x8000):
        memory[bank + 0x0280:bank + 0x02A8] = memory[bank + 0x2280:bank + 0x22A8]
        memory[bank + 0x03F8:bank + 0x0400] = memory[bank + 0x23F8:bank + 0x2400]
    return memory


def decode_field(data, field, variant=None):
    memory = memory_image(data)
    output, owners = bytearray(64000), {"bitmap": 0, "sprite": 0, "paper": 0, "left_blanking": 0, "left_bitmap": 0}
    field_base = field * 0x8000
    for y in range(200):
        page = (0x4000 + (((~y >> 1) & 7) << 10) if y < 128 else
                0x2000 + ((((y >> 1) + (1 if y >= 168 else 0)) & 3) << 10)) + field_base
        sprite_base = field_base + (0x4000 if y < 128 else 0)
        within = ((((y + 47) // 2) * 3) + (0 if y < 123 else 1 if y < 165 else 2)) & 63
        for x in range(320):
            column = x // 8
            cell = (y // 8) * 40 + column
            attributes = memory[page + cell]
            bitmap = memory[field_base + (0x6000 if y < 128 else 0x2000) + cell * 8 + (y & 7)]
            if variant == "no_bitmap":
                bitmap = 0
            if x < 24:
                foreground = bool(bitmap & (128 >> (x & 7)))
                output[y * 320 + x] = 15 if foreground else 0
                owners["left_bitmap" if foreground else "left_blanking"] += 1
                continue
            color, owner = attributes & 15, "paper"
            if bitmap & (128 >> (x & 7)):
                color, owner = attributes >> 4, "bitmap"
            elif x < 312 and variant != "no_sprites":
                sprite = 1 + (x - 24) // 48
                sx = ((x - 24) // 2) % 24
                pointer = memory[page + 0x3F8 + sprite]
                bits = memory[sprite_base + pointer * 64 + ((within + sx // 8) & 63)]
                if bits & (128 >> (sx & 7)):
                    row = (y + 1) // 2
                    color_address = field_base + (0x2400, 0x2480, 0x2800, 0x2880, 0x2C00, 0x2C80)[sprite - 1]
                    color, owner = memory[color_address + row], "sprite"
            if not 0 <= color <= 15:
                raise ValueError("Decoded a nonphysical VIC color")
            output[y * 320 + x] = color
            owners[owner] += 1
    return bytes(output), owners
