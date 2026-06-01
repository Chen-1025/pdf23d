"""Classify PDF pages by content and group into logical furniture/room units.

Uses keyword matching on Chinese labels + dimension-based heuristics.
"""
from __future__ import annotations
from typing import Any

# Page-level classification based on content labels
# (keyword_list, furniture_type, room_name)
FURNITURE_RULES = [
    # Kitchen
    (['厨房'], 'kitchen_cabinet', '厨房'),
    (['灶具', '烟机', '水槽', '洗碗机', '调味拉篮', '碗篮'], 'kitchen_appliance', '厨房'),
    # Living room
    (['电视柜', '电视墙', '电视背景'], 'tv_cabinet', '客厅'),
    (['开放格', '展示'], 'shelving', '客厅'),
    # Entrance
    (['鞋柜', '入户柜', '玄关'], 'entrance_cabinet', '玄关'),
    # Wardrobe / Bedroom
    (['衣柜', '挂衣区', '叠放区', '长衣区', '短衣区', '裤架', '衣帽间'], 'wardrobe', '卧室'),
    (['榻榻米', '床头柜', '床'], 'bedroom_furniture', '卧室'),
    (['收纳柜', '储物'], 'storage', '卧室'),
    # Study
    (['书桌', '书柜', '电脑桌', '办公'], 'study_furniture', '书房'),
    # Dining
    (['餐边柜', '酒柜', '餐桌'], 'sideboard', '餐厅'),
    # Bathroom
    (['浴室柜', '镜柜'], 'bathroom_cabinet', '卫生间'),
    # Balcony
    (['阳台柜', '洗衣柜', '洗衣机'], 'balcony_cabinet', '阳台'),
    # Generic cabinet fallback
    (['吊柜', '地柜'], 'kitchen_cabinet', '厨房'),
    (['高柜'], 'tall_cabinet', '卧室'),
    (['柜'], 'cabinet', '房间'),
]


def classify_page(text_blocks: list[dict], plain_text: str) -> dict[str, Any]:
    """Classify a page from its text content."""
    all_text = ''.join(t["text"] for t in text_blocks)

    # Determine furniture type from keywords
    furniture_type = "unknown"
    room_name = "房间"
    for keywords, ftype, room in FURNITURE_RULES:
        if any(k in all_text for k in keywords):
            furniture_type = ftype
            room_name = room
            break

    # Determine page type
    page_type = "cabinet_drawing"
    if any(k in all_text for k in ['平面', '俯视', '布置图', '布局图']):
        page_type = "floor_plan"
    elif any(k in all_text for k in ['立面', '正视', '侧视', '外观']):
        page_type = "elevation"
    elif any(k in all_text for k in ['剖面', '剖视', '内部', '结构']):
        page_type = "section"
    elif any(k in all_text for k in ['大样', '详图', '节点']):
        page_type = "detail"

    # Extract dimension numbers and labels
    import re
    dims = []
    labels = []
    materials = []
    for t in text_blocks:
        txt = t["text"].strip()
        if re.match(r'^\d{2,4}$', txt):
            dims.append({"value": int(txt), "pos": t["bbox"]})
        elif re.match(r'^\d+[\*×xX]\d+$', txt):
            dims.append({"value": txt, "pos": t["bbox"]})
        elif 'PET' in txt.upper():
            materials.append(txt)
        elif len(txt) >= 2:
            labels.append(txt)

    # Project mark
    project = ""
    for lb in labels:
        m = re.search(r'(\d{2,3}-\d{4})', lb)
        if m:
            project = m.group(1)
            break

    num_dims = sorted([d["value"] for d in dims if isinstance(d["value"], int)], reverse=True)
    max_dim = max(num_dims) if num_dims else 0

    # Material type
    material = ""
    for m in materials:
        if '冰山白' in m:
            material = "iceberg_white"
        elif '天鹅白' in m:
            material = "swan_white"

    # Cabinet dimension hints from dimension patterns
    width_est = max_dim
    height_est = num_dims[1] if len(num_dims) > 1 else 2800
    depth_est = 400

    # Look for depth in labels
    for lb in labels:
        m = re.search(r'[深厚]度?\s*[:：]?\s*(\d{2,4})', lb)
        if m:
            depth_est = int(m.group(1))
            break
    # Estimate depth from dimension patterns
    for d in num_dims:
        if 300 <= d <= 650:
            depth_est = d
            break

    return {
        "type": page_type,
        "furniture_type": furniture_type,
        "room_name": room_name,
        "project": project,
        "material": material,
        "dimensions": num_dims[:20],
        "max_dim": max_dim,
        "dim_count": len(dims),
        "estimated_width": width_est,
        "estimated_height": height_est,
        "estimated_depth": depth_est,
        "materials": materials,
        "labels": labels,
    }


def group_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group pages into rooms based on room_name."""
    rooms: dict[str, dict] = {}
    for page in pages:
        info = page["classification"]
        room_key = info["room_name"]

        if room_key not in rooms:
            rooms[room_key] = {
                "id": f"room_{len(rooms)+1}",
                "name": room_key,
                "pages": [],
                "project": info["project"],
            }

        rooms[room_key]["pages"].append({
            "page_num": page["page_num"] + 1,
            "type": info["type"],
            "furniture_type": info["furniture_type"],
            "room_name": info["room_name"],
            "dimensions": info["dimensions"],
            "max_dim": info["max_dim"],
            "est_width": info["estimated_width"],
            "est_height": info["estimated_height"],
            "est_depth": info["estimated_depth"],
            "material": info["material"],
            "labels": info["labels"][:10],
        })

    result = list(rooms.values())
    # Sort by first page number
    result.sort(key=lambda r: r["pages"][0]["page_num"])
    return result
