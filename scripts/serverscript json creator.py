# Server Script
# Script Type: Scheduler Event
# Frequency: Hourly/Daily
#
# Goal: write /files/products.json (public) containing an array of product dicts
# Constraint: assume NOTHING is exposed except builtins + frappe APIs available in Server Script.

OUT_FILENAME = "website-products.json"
OUT_FOLDER = "Home"
ONLY_PUBLISH = 0  # 1 => include only publish_item=1

# Fieldnames (adjust to your custom fields)
F_EXTERNAL_NAME = "custom_external_name"
F_PANJANG = "custom_panjang"
F_LEBAR = "custom_lebar"
F_TINGGI = "custom_tinggi"
F_BERAT = "weight_per_unit"
F_WEBSITE_DESC = "custom_website_description"
F_CBM = "custom_cbm"
F_PUBLISH = "custom_publish_item"
F_INCLUDE_WEBSITE = "custom_include_in_website" 
ERP_BASE = "https://kirun.pttimboel.com"   # no trailing slash
ALLOW_PRIVATE = 0                          # 1 = include private URLs (not usable for static)

# ----------------------------
# Helpers: numbers + slug
# ----------------------------
def as_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        return int(float(v))
    except Exception:
        return default

def as_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def make_slug(s):
    s = (s or "").lower()
    for ch in [" ", "/", "\\", "_", ",", ".", "(", ")", "[", "]", "{", "}", "+", "&", ":", ";", "!", "?", "@", "#", "$", "%", "^", "*", "=", "|", "<", ">", "~", "`", "'"]:
        s = s.replace(ch, "-")
    out = ""
    for c in s:
        if c.isalnum() or c == "-":
            out += c
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")

# ----------------------------
# Helpers: JSON serializer (no json module)
# ----------------------------
def j_escape(s):
    s = "" if s is None else str(s)
    s = s.replace("\\", "\\\\")
    s = s.replace('"', '\\"')
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    s = s.replace("\t", "\\t")
    return '"' + s + '"'

def j_dump(v):
    if v is None:
        return "null"

    if isinstance(v, bool):
        return "true" if v else "false"

    if isinstance(v, int):
        return str(v)

    if isinstance(v, float):
        if v != v or v == float("inf") or v == -float("inf"):
            return "0"
        return str(v)

    if isinstance(v, str):
        return j_escape(v)

    if isinstance(v, list) or isinstance(v, tuple):
        return "[" + ",".join([j_dump(x) for x in v]) + "]"

    if isinstance(v, dict):
        parts = []
        for k, val in v.items():  # preserve insertion order
            parts.append(j_escape(k) + ":" + j_dump(val))
        return "{" + ",".join(parts) + "}"

    return j_escape(v)


# ----------------------------
# Data extraction
# ----------------------------

def normalize_file_url(u):
    if not u:
        return None
    u = str(u).strip()

    # already absolute
    if u.startswith("http://") or u.startswith("https://"):
        return u

    # private not usable for static
    if u.startswith("/private/files/"):
        if ALLOW_PRIVATE:
            return ERP_BASE + u
        return None

    # public files (and any other root path)
    if u.startswith("/"):
        return ERP_BASE + u

    # weird relative path -> drop
    return None
    
def get_tags(item_code):
    rows = frappe.get_all(
        "Tag Link",
        filters={"document_type": "Item", "document_name": item_code},
        fields=["tag"],
        limit_page_length=200
    )
    return [(r.get("tag") or "").strip() for r in rows if (r.get("tag") or "").strip()]
    
def extract_collections(raw_tags):
    collections = []
    seen = set()

    for tag in raw_tags or []:
        if not tag:
            continue

        t = str(tag).strip()
        if not t:
            continue

        low = t.lower()
        if low.startswith("col:"):
            val = t[4:].strip()
            if val:
                key = val.lower()
                if key not in seen:
                    seen.add(key)
                    collections.append(val)

    return collections


def extract_tags(raw_tags):
    tags = []
    seen = set()

    for tag in raw_tags or []:
        if not tag:
            continue

        t = str(tag).strip()
        if not t:
            continue

        low = t.lower()

        if low.startswith("col:"):
            continue

        if low not in seen:
            seen.add(low)
            tags.append(t)

    return tags



def get_images(item_code):
    out = []

    files = frappe.get_all(
        "File",
        filters={
            "attached_to_doctype": "Item",
            "attached_to_name": item_code,
            "is_private": 0,
            "custom_include_in_website": 1
        },
        fields=[
            "name",
            "file_url",
            "file_name",
            "custom_image_role",
        ],
        order_by="creation asc",
        limit_page_length=500
    )

    seen = set()
    for f in files:
        u = f.get("file_url")
        nu = normalize_file_url(u)
        if not nu:
            continue
        if nu in seen:
            continue
        seen.add(nu)

        out.append({
            "url": nu,
            "file_id": f.get("name"),
            "file_name": f.get("file_name") or "",
            "role": (f.get("custom_image_role") or "gallery"),
        })

    return out


filters = {"disabled": 0, F_INCLUDE_WEBSITE: 1}
if ONLY_PUBLISH:
    filters[F_PUBLISH] = 1

fields = [
    "name as item_code",
    "item_name",
    F_EXTERNAL_NAME + " as external_name",
    F_PANJANG + " as panjang",
    F_LEBAR + " as lebar",
    F_TINGGI + " as tinggi",
    F_BERAT + " as berat",
    F_WEBSITE_DESC + " as website_description",
    F_CBM + " as cbm",
    F_PUBLISH + " as publish_item",
]

items = frappe.get_all("Item", filters=filters, fields=fields, limit_page_length=100000)

out = []
for it in items:
    item_code = it.get("item_code")
    if not item_code:
        continue

    item_name = it.get("item_name") or ""
    external_name = it.get("external_name") or ""
    website_description = it.get("website_description") or ""
    publish_item = as_int(it.get("publish_item"), 0)

    slug = make_slug(item_name)
    raw_tags = get_tags(item_code)
    collections = extract_collections(raw_tags)
    tags = extract_tags(raw_tags)
    images = get_images(item_code)

    out.append({
        "item_code": item_code,
        "item_name": item_name,
        "slug": slug,
        "external_name": external_name,
        "panjang": as_int(it.get("panjang")),
        "lebar": as_int(it.get("lebar")),
        "tinggi": as_int(it.get("tinggi")),
        "berat": as_float(it.get("berat")),
        "website_description": website_description,
        "cbm": as_float(it.get("cbm")),
        "publish_item": publish_item,
        "collection_list": collections, 
        "tags": tags,
        "images": images,
    })

# stable ordering
out = sorted(out, key=lambda x: x.get("item_code") or "")

payload = j_dump(out)

# ----------------------------
# Replace File every run (forces disk file rewrite)
# ----------------------------
existing = frappe.get_all(
    "File",
    filters={"file_name": OUT_FILENAME, "is_private": 0},
    fields=["name"],
    limit_page_length=50,
)

for r in existing:
    try:
        frappe.get_doc("File", r["name"]).delete(ignore_permissions=True)
    except Exception:
        pass

f = frappe.get_doc({
    "doctype": "File",
    "file_name": OUT_FILENAME,
    "content": payload,
    "folder": OUT_FOLDER,
    "is_private": 0,
})
f.insert(ignore_permissions=True)

frappe.db.commit()
