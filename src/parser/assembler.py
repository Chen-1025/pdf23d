"""Convert grouped page data into structured room/cabinet model JSON."""
from __future__ import annotations
from typing import Any

ROOM_SIZES = {
    "厨房": (3000, 2500),
    "客厅": (5000, 4200),
    "卧室": (4200, 3600),
    "书房": (3000, 2800),
    "餐厅": (3500, 3000),
    "玄关": (2000, 1800),
    "卫生间": (2500, 2000),
    "阳台": (3500, 1500),
    "储物间": (2000, 2000),
    "房间": (4000, 3500),
}

# Floor plan layout offsets (x, z) for each room type
# Arranges rooms in a column layout:
#   厨房 | 餐厅
#   客厅 (wide)
#   卧室 | 书房
#   房间 (wide)
ROOM_LAYOUTS: list[list[str]] = [
    ["厨房", "餐厅"],
    ["客厅"],
    ["卧室", "书房"],
    ["房间"],
]

# Center the entire layout at origin (offset subtracted after layout)
LAYOUT_CENTER_X = 4000  # center x offset
LAYOUT_CENTER_Z = 7500  # center z offset


def _compute_room_offsets(room_names: list[str]) -> dict[str, tuple[int, int]]:
    """Compute world-space offsets for each room, centered on origin."""
    offsets = {}
    z_offset = 0
    for row in ROOM_LAYOUTS:
        row_rooms = [r for r in row if r in room_names]
        if not row_rooms:
            continue
        row_height = 0
        x_offset = 0
        for rname in row_rooms:
            rw, rd = ROOM_SIZES.get(rname, (4000, 3500))
            offsets[rname] = (x_offset, z_offset)
            x_offset += rw + 1000
            row_height = max(row_height, rd)
        z_offset += row_height + 1000

    # Compute bounding box of all rooms
    max_x = 0
    max_z = 0
    for rname, (ox, oz) in offsets.items():
        rw, rd = ROOM_SIZES.get(rname, (4000, 3500))
        max_x = max(max_x, ox + rw)
        max_z = max(max_z, oz + rd)

    # Center the entire layout
    cx = max_x // 2
    cz = max_z // 2
    return {rn: (ox - cx, oz - cz) for rn, (ox, oz) in offsets.items()}


def build_room_model(groups: list[dict[str, Any]], project_name: str = "") -> dict[str, Any]:
    room_names = [g["name"] for g in groups]
    offsets = _compute_room_offsets(room_names)

    rooms = []
    for group in groups:
        room_name = group["name"]
        room_w, room_d = ROOM_SIZES.get(room_name, (4000, 3500))
        ox, oz = offsets.get(room_name, (0, 0))

        walls = [
            {"id": f"{group['id']}_s", "length": room_w, "height": 2800, "thickness": 120,
             "start": [ox, oz], "end": [ox + room_w, oz]},
            {"id": f"{group['id']}_e", "length": room_d, "height": 2800, "thickness": 120,
             "start": [ox + room_w, oz], "end": [ox + room_w, oz + room_d]},
            {"id": f"{group['id']}_n", "length": room_w, "height": 2800, "thickness": 120,
             "start": [ox + room_w, oz + room_d], "end": [ox, oz + room_d]},
            {"id": f"{group['id']}_w", "length": room_d, "height": 2800, "thickness": 120,
             "start": [ox, oz + room_d], "end": [ox, oz]},
        ]

        cabinets = []
        for p in group["pages"]:
            cab = _build_cabinet(p, group["id"])
            if cab:
                cabinets.append(cab)

        # Position cabinets: spread across south and north walls to avoid overlap
        n_cabs = len(cabinets)
        if n_cabs == 0:
            pass
        elif n_cabs == 1:
            cabinets[0]["position"] = [ox + (room_w - cabinets[0]["width"]) // 2, oz + 50]
        else:
            # Split between south (oz) and north (oz + room_d - depth) walls
            south_cabs = cabinets[::2]  # even indices → south wall
            north_cabs = cabinets[1::2]  # odd indices → north wall

            def place_row(cab_list, z_pos):
                if not cab_list:
                    return
                n = len(cab_list)
                total_w = sum(c["width"] for c in cab_list)
                gap = max(50, (room_w - 400 - total_w) // max(n - 1, 1))
                # If total exceeds available, scale down
                if total_w > room_w - 400:
                    scale = (room_w - 400) / total_w
                    for c in cab_list:
                        c["width"] = max(150, int(c["width"] * scale))
                    total_w = sum(c["width"] for c in cab_list)
                    gap = max(30, (room_w - 400 - total_w) // max(n - 1, 1))
                x_pos = ox + 200
                for c in cab_list:
                    c["position"] = [x_pos, z_pos]
                    x_pos += c["width"] + gap

            place_row(south_cabs, oz + 50)
            place_row(north_cabs, oz + room_d - max(c["depth"] for c in north_cabs) - 50 if north_cabs else oz + 50)

        rooms.append({
            "name": room_name,
            "floor": {"width": room_w, "depth": room_d, "material": "floor_wood",
                      "offset_x": ox, "offset_z": oz},
            "walls": walls,
            "cabinets": cabinets,
            "openings": [],
        })

    return {"project": project_name, "rooms": rooms}


def _build_cabinet(page: dict, group_id: str) -> dict | None:
    dims = page.get("dimensions", [])
    if not dims:
        return None

    # Separate dimensions into categories
    small = sorted([d for d in dims if 20 <= d <= 100])   # thickness, gaps
    medium = sorted([d for d in dims if 150 <= d <= 650])  # depth, door width
    large = sorted([d for d in dims if 700 <= d <= 3000])  # width, height

    if not large:
        return None

    # Width = largest "large" dimension
    width = max(large)
    # Height = second largest dimension, capped by cabinet type
    cab_type = page.get("furniture_type", "cabinet")
    height = large[-2] if len(large) >= 2 else 2600
    # Cap heights based on type
    type_max_heights = {
        "kitchen_cabinet": 900, "kitchen_appliance": 2200,
        "tv_cabinet": 600, "shelving": 1200, "sideboard": 1100,
        "entrance_cabinet": 2400, "wardrobe": 2600,
        "study_furniture": 2200, "cabinet": 2400,
        "bedroom_furniture": 2200, "storage": 2400,
        "tall_cabinet": 2600,
    }
    max_h = type_max_heights.get(cab_type, 2400)
    if height > max_h:
        height = max_h
    if height > 2800:
        height = 2600
    if height < 400:
        height = 720

    # Depth from medium dimensions or default
    depth = 400
    if medium:
        # Most common medium value is likely the depth
        depth = max(set(medium), key=medium.count) if len(medium) > 1 else medium[0]
    # Check labels for explicit depth
    for lb in page.get("labels", []):
        import re
        m = re.search(r'[深厚]度?\s*[:：]?\s*(\d{2,4})', lb)
        if m:
            depth = int(m.group(1))
            break

    return {
        "id": f"{group_id}_cab_{page['page_num']}",
        "type": page.get("furniture_type", "cabinet"),
        "width": width,
        "height": height,
        "depth": depth,
        "position": [0, 0],
        "material": "PET/9" if page.get("material") == "swan_white" else "PET/40",
        "source_page": page["page_num"],
    }
