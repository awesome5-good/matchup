import requests
from supabase import create_client

SUPABASE_URL = "https://wykupodtnbcrebgbzyxr.supabase.co"
SUPABASE_KEY = "sb_publishable_THekjy2-GusHmZ7FrjX9UQ_gm41EUr2"
API_KEY = "4f518baf8a28ed0f517bba932b36bc8dccb2b3c5c5b16993de091777e0f48ef4"

db = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_save():
    url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
    params = {
        "serviceKey": API_KEY,
        "page": 1,
        "perPage": 100,
        "returnType": "JSON"
    }
    print("K-Startup API 호출 중...")
    res = requests.get(url, params=params, timeout=10)
    data = res.json()
    items = data.get("data", [])
    print(f"공고 {len(items)}건 수신")

    saved = 0
    for item in items:
        # 마감일 변환
        deadline = item.get("pbanc_rcpt_end_dt")
        if deadline and len(deadline) == 8:
            deadline = f"{deadline[:4]}-{deadline[4:6]}-{deadline[6:8]}"
        else:
            deadline = None

        # 태그 구성
        tags = ["K-Startup"]
        category = item.get("supt_biz_clsfc", "")
        region = item.get("supt_regin", "")
        if category:
            tags.append(category)
        if region:
            tags.append(region)

        program = {
            "title": item.get("biz_pbanc_nm", ""),
            "organization": item.get("pbanc_ntrp_nm", ""),
            "category": category or "창업",
            "description": item.get("pbanc_ctnt", ""),
            "deadline": deadline,
            "eligibility": item.get("aply_trgt_ctnt", ""),
            "source_url": item.get("detl_pg_url", ""),
            "tags": tags,
            "is_active": True
        }

        if not program["title"]:
            continue

        try:
            db.table("programs").insert(program).execute()
            saved += 1
            print(f"저장: {program['title'][:40]}")
        except Exception as e:
            print(f"오류: {e}")

    print(f"\n완료! {saved}건 저장됨")

fetch_and_save()