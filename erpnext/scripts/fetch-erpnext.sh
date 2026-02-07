#!/usr/bin/env bash
set -euo pipefail

: "${ERPNEXT_BASE_URL:?set https://kirun.pttimboel.com}"
: "${ERPNEXT_API_KEY:?set a3f002a5706c14e}"
: "${ERPNEXT_API_SECRET:?set 8012f2d5013cc56}"

AUTH_HEADER="Authorization: token ${ERPNEXT_API_KEY}:${ERPNEXT_API_SECRET}"
OUT_DIR="data/erpnext"
mkdir -p "${OUT_DIR}"

curl_json () {
  local url="$1"
  local out="$2"
  curl -fsSL \
    -H "${AUTH_HEADER}" \
    -H "Accept: application/json" \
    "${url}" > "${out}"
}

# 1) Items (core + child table collections)
# NOTE: adjust fieldnames if yours differ.
ITEM_FIELDS='[
  "name",
  "item_name",
  "image",
  "modified",
  "custom_external_name",
  "custom_description_md",
  "custom_material",
  "custom_size_display",
  "custom_finishing_name",
  "custom_published",
  "custom_slug",
  "custom_collections"
]'

ITEM_FILTERS='[
  ["disabled","=",0]
]'

ITEM_URL="${ERPNEXT_BASE_URL}/api/resource/Item?fields=$(python3 -c "import urllib.parse,sys,json; print(urllib.parse.quote(sys.argv[1]))" "${ITEM_FIELDS}")&filters=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${ITEM_FILTERS}")&limit_page_length=5000"

curl_json "${ITEM_URL}" "${OUT_DIR}/items.json"

# 2) Collections master (slug lookup)
COLLECTION_FIELDS='["name","slug"]'
COLLECTION_URL="${ERPNEXT_BASE_URL}/api/resource/Timboel%20Collection?fields=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${COLLECTION_FIELDS}")&limit_page_length=5000"
curl_json "${COLLECTION_URL}" "${OUT_DIR}/collections.json"

# 3) Tag Links (tags per item)
TAG_FIELDS='["tag","document_name"]'
TAG_FILTERS='[
  ["document_type","=","Item"]
]'
TAG_URL="${ERPNEXT_BASE_URL}/api/resource/Tag%20Link?fields=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${TAG_FIELDS}")&filters=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${TAG_FILTERS}")&limit_page_length=5000"
curl_json "${TAG_URL}" "${OUT_DIR}/tag_links.json"

# 4) Files (attachments per item)
FILE_FIELDS='["file_url","attached_to_name","creation"]'
FILE_FILTERS='[
  ["attached_to_doctype","=","Item"],
  ["is_folder","=",0]
]'
FILE_URL="${ERPNEXT_BASE_URL}/api/resource/File?fields=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${FILE_FIELDS}")&filters=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "${FILE_FILTERS}")&order_by=creation%20asc&limit_page_length=5000"
curl_json "${FILE_URL}" "${OUT_DIR}/files.json"

echo "OK: wrote ${OUT_DIR}/items.json collections.json tag_links.json files.json"

