BASE_URL = "https://is3.cloudhost.id/image-timboel/product-img/"
MAX_INDEX = 10
MISS_THRESHOLD = 2

storage_groups = {
    "depan": ["detail","gallery","box","story"],
    "kiri": ["detail","gallery","box","story"],
    "kanan": ["detail","gallery","box","story"],
    "belakang": ["detail","gallery","box","story"],
    "sudut": ["detail","gallery","box","story","hero","thumbnail","hbanner"],
    "interior": ["detail","gallery","hero"],
    "exterior": ["detail","gallery","hero"],
}

for storage, resolutions in storage_groups.items():
    for res in resolutions:
        miss = 0  # consecutive misses for this (storage,res)

        for i in range(0, MAX_INDEX + 1):
            nn = "" if i == 0 else str(i).zfill(2)
            url = f"{BASE_URL}{doc.item_code}_{storage}{nn}_{res}.jpg"

            # GET existence check
            try:
                frappe.make_get_request(url)
            except Exception as e:
                miss += 1
                frappe.log_error(
                    f"MISS item={doc.item_code} storage={storage} res={res} i={i} miss={miss}\nurl={url}\nerr={repr(e)}",
                    "IMAGE EXISTS FAIL"
                )
                if miss >= MISS_THRESHOLD:
                    break
                continue

            # success path
            miss = 0

            # attach (idempotent)
            if not frappe.db.exists("File", {
                "attached_to_doctype": "Item",
                "attached_to_name": doc.name,
                "file_url": url,
            }):
                try:
                    frappe.get_doc({
                        "doctype": "File",
                        "file_name": f"{storage.title()}{nn} {res.title()}.jpg",
                        "file_url": url,
                        "is_private": 0,
                        "attached_to_doctype": "Item",
                        "attached_to_name": doc.name,
                    }).insert(ignore_permissions=True)
                    # frappe.log_error(f"ATTACHED url={url}", "IMAGE ATTACH OK")
                except Exception as e:
                    continue
                    # frappe.log_error(f"url={url}\nerr={repr(e)}", "FILE INSERT FAILED")
