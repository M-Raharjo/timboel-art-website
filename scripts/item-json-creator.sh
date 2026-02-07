#item-json-creator
#!/usr/bin/env bash
set -euo pipefail

# ========= CONFIG =========
ERP_URL="${ERP_URL:-https://your-erp.example.com}"          # no trailing slash
API_KEY="${API_KEY:-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx}"
API_SECRET="${API_SECRET:-yyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy}"
OUT_FILE="${OUT_FILE:-items.website.json}"

# Item fieldnames
FIELD_EXTERNAL_NAME="${FIELD_EXTERNAL_NAME:-custom_external_name}"
FIELD_PANJANG="${FIELD_PANJANG:-custom_panjang}"
FIELD_LEBAR="${FIELD_LEBAR:-custom_lebar}"
FIELD_TINGGI="${FIELD_TINGGI:-custom_tinggi}"
FIELD_BERAT="${FIELD_BERAT:-weight_per_unit}"
FIELD_WEBSITE_DESC="${FIELD_WEBSITE_DESC:-custom_website_description}"
FIELD_CBM="${FIELD_CBM:-custom_cbm}"
FIELD_WEBSITE_TICK="${FIELD_WEBSITE_TICK:-custom_include_in_website}"     # filter = 1
FIELD_PUBLISH_TICK="${FIELD_PUBLISH_TICK:-custom_publish_item}"           # output

# Child table fieldname on Item for collections
FIELD_COLLECTION_TABLE="${FIELD_COLLECTION_TABLE:-custom_collection}"
FIELD_COLLECTION_VALUE="${FIELD_COLLECTION_VALUE:-timboel_collection}"

# ========= HELPERS =========
AUTH_HEADER="Authorization: token ${API_KEY}:${API_SECRET}"

curl_get() {
  local path="$1"; shift
  curl -sS \
    -H "${AUTH_HEADER}" \
    -H "Accept: application/json" \
    --get \
    "$@" \
    "${ERP_URL}${path}"
}

# ========= 1) LIST ITEM *NAMES* (NAME == ITEM_CODE) =========
# You insist: Item.name is the item_code. This script assumes that is true.
LIST_JSON="$(
  curl_get "/api/resource/Item" \
    --data-urlencode 'fields=["name","item_code"]' \
    --data-urlencode "filters=[[\"${FIELD_WEBSITE_TICK}\",\"=\",1]]" \
    --data-urlencode 'limit_page_length=0'
)"

tmp="$(mktemp)"
echo "[]" > "$tmp"

# Loop keys: name (which you enforce equals item_code)
mapfile -t ITEM_KEYS < <(echo "$LIST_JSON" | jq -r '.data[].name')

for key in "${ITEM_KEYS[@]}"; do
  # Full item doc (by name == item_code)
  DOC="$(
    curl_get "/api/resource/Item/${key}" \
      --data-urlencode 'fields=["*"]'
  )"

  # Attachments linked to this Item (attached_to_name == Item.name == item_code)
  FILES="$(
    curl_get "/api/resource/File" \
      --data-urlencode 'fields=["file_url","file_name","is_private"]' \
      --data-urlencode "filters=[[\"File\",\"attached_to_doctype\",\"=\",\"Item\"],[\"File\",\"attached_to_name\",\"=\",\"${key}\"]]" \
      --data-urlencode 'limit_page_length=0'
  )"

  ITEM_OBJ="$(jq -n \
    --argjson doc "$(echo "$DOC" | jq '.data')" \
    --argjson files "$(echo "$FILES" | jq '.data')" \
    --arg f_ext "$FIELD_EXTERNAL_NAME" \
    --arg f_p "$FIELD_PANJANG" \
    --arg f_l "$FIELD_LEBAR" \
    --arg f_t "$FIELD_TINGGI" \
    --arg f_b "$FIELD_BERAT" \
    --arg f_desc "$FIELD_WEBSITE_DESC" \
    --arg f_cbm "$FIELD_CBM" \
    --arg f_pub "$FIELD_PUBLISH_TICK" \
    --arg f_ctab "$FIELD_COLLECTION_TABLE" \
    --arg f_cval "$FIELD_COLLECTION_VALUE" \
    '
    def to_tags($s):
      if ($s == null or $s == "") then []
      else ($s | split(",") | map(gsub("^\\s+|\\s+$";"")) | map(select(. != "")))
      end;

    def slugify($name):
      ($name // "")
      | ascii_downcase
      | gsub("[^a-z0-9]+"; "-")
      | gsub("^-+|-+$"; "");


    {
      item_code: ($doc.item_code // $doc.name),
      item_name: ($doc.item_name // ""),
      slug: slugify($doc.item_name // ""),
      external_name: ($doc[$f_ext] // ""),
      panjang: ($doc[$f_p] // null),
      lebar: ($doc[$f_l] // null),
      tinggi: ($doc[$f_t] // null),
      berat: ($doc[$f_b] // null),
      website_description: ($doc[$f_desc] // ""),
      cbm: ($doc[$f_cbm] // null),

      publish_item: ($doc[$f_pub] // 0),

      collection_list: (
        ($doc[$f_ctab] // [])
        | map(.[$f_cval] // .collection // .name // .title // empty)
        | map(select(. != null and . != ""))
      ),

      tags: to_tags($doc._user_tags),

      images: (
        $files
        | map(.file_url)
        | map(select(. != null and . != ""))
      )
    }
  ')"

  jq --argjson item "$ITEM_OBJ" '. + [$item]' "$tmp" > "${tmp}.next"
  mv "${tmp}.next" "$tmp"
done

jq '.' "$tmp" > "$OUT_FILE"
rm -f "$tmp"

echo "Wrote: $OUT_FILE"
