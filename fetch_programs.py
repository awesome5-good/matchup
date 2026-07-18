# -*- coding: utf-8 -*-
"""
매치업 지원사업 데이터 수집 v2
- K-Startup: 페이지네이션 (최대 5페이지 = 500건)
- 기업마당(Bizinfo): API 키 입력 시 자동 활성화
- upsert로 중복 방지 (title 기준)
- 마감 지난 공고 자동 비활성화
실행: python fetch_programs.py
"""
import requests
from datetime import date
from supabase import create_client

SUPABASE_URL = "https://wykupodtnbcrebgbzyxr.supabase.co"
SUPABASE_KEY = "sb_publishable_THekjy2-GusHmZ7FrjX9UQ_gm41EUr2"
KSTARTUP_KEY = "4f518baf8a28ed0f517bba932b36bc8dccb2b3c5c5b16993de091777e0f48ef4"

# 기업마당 인증키 — https://www.bizinfo.go.kr/apiList.do 에서 발급 후 여기 입력
BIZINFO_KEY = "2I57xn"

db = create_client(SUPABASE_URL, SUPABASE_KEY)
today = date.today().isoformat()


def fmt_date(s):
    """YYYYMMDD 또는 YYYY-MM-DD → YYYY-MM-DD, 아니면 None"""
    if not s:
        return None
    s = str(s).strip().replace(".", "-").replace("/", "-")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return None


def upsert_program(program):
    """title 기준 upsert — 이미 있으면 갱신, 없으면 삽입"""
    try:
        db.table("programs").upsert(program, on_conflict="title").execute()
        return True
    except Exception as e:
        print(f"  upsert 오류: {e}")
        return False


def fetch_kstartup():
    print("=" * 50)
    print("[1/3] K-Startup API 수집 시작")
    url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
    total = 0
    for page in range(1, 6):  # 최대 5페이지 = 500건
        params = {
            "serviceKey": KSTARTUP_KEY,
            "page": page,
            "perPage": 100,
            "returnType": "JSON",
        }
        try:
            res = requests.get(url, params=params, timeout=15)
            data = res.json()
        except Exception as e:
            print(f"  페이지 {page} 호출 실패: {e}")
            break

        items = data.get("data", [])
        if not items:
            print(f"  페이지 {page}: 데이터 없음 — 종료")
            break
        print(f"  페이지 {page}: {len(items)}건 수신")

        for item in items:
            title = (item.get("biz_pbanc_nm") or "").strip()
            if not title:
                continue
            deadline = fmt_date(item.get("pbanc_rcpt_end_dt"))
            # 마감 지난 공고는 저장 단계에서 제외
            if deadline and deadline < today:
                continue

            category = item.get("supt_biz_clsfc", "") or "창업"
            region = item.get("supt_regin", "") or ""
            tags = ["K-Startup"]
            if category:
                tags.append(category)
            if region:
                tags.append(region)

            program = {
                "title": title,
                "organization": item.get("pbanc_ntrp_nm", ""),
                "category": category,
                "description": item.get("pbanc_ctnt", ""),
                "deadline": deadline,
                "eligibility": item.get("aply_trgt_ctnt", ""),
                "source_url": item.get("detl_pg_url", ""),
                "tags": tags,
                "is_active": True,
            }
            if upsert_program(program):
                total += 1
    print(f"  → K-Startup 완료: {total}건 저장/갱신")
    return total


def fetch_bizinfo():
    print("=" * 50)
    if not BIZINFO_KEY:
        print("[2/3] 기업마당 — 인증키 미입력, 건너뜀")
        print("  발급: https://www.bizinfo.go.kr/apiList.do → 지원사업정보 API")
        return 0
    print("[2/3] 기업마당 API 수집 시작")
    url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    params = {
        "crtfcKey": BIZINFO_KEY,
        "dataType": "json",
        "searchCnt": "300",
    }
    total = 0
    try:
        res = requests.get(url, params=params, timeout=20)
        data = res.json()
    except Exception as e:
        print(f"  호출 실패: {e}")
        return 0

    items = data.get("jsonArray", []) or data.get("item", []) or []
    print(f"  {len(items)}건 수신")
    for item in items:
        title = (item.get("pblancNm") or "").strip()
        if not title:
            continue
        # 신청기간 "20260101 ~ 20260731" 형태에서 종료일 추출
        period = item.get("reqstBeginEndDe", "") or ""
        deadline = None
        if "~" in period:
            deadline = fmt_date(period.split("~")[-1].strip())
        if deadline and deadline < today:
            continue

        category = item.get("pldirSportRealmLclasCodeNm", "") or "경영"
        organ = item.get("jrsdInsttNm", "") or item.get("excInsttNm", "")
        tags = ["기업마당", category]

        detail_url = item.get("pblancUrl", "") or ""
        if detail_url and detail_url.startswith("/"):
            detail_url = "https://www.bizinfo.go.kr" + detail_url

        program = {
            "title": title,
            "organization": organ,
            "category": category,
            "description": (item.get("bsnsSumryCn") or "")[:2000],
            "deadline": deadline,
            "eligibility": item.get("trgetNm", "") or "",
            "source_url": detail_url,
            "tags": tags,
            "is_active": True,
        }
        if upsert_program(program):
            total += 1
    print(f"  → 기업마당 완료: {total}건 저장/갱신")
    return total


def deactivate_expired():
    print("=" * 50)
    print("[3/3] 마감 지난 공고 비활성화")
    try:
        res = (
            db.table("programs")
            .update({"is_active": False})
            .lt("deadline", today)
            .eq("is_active", True)
            .execute()
        )
        cnt = len(res.data) if res.data else 0
        print(f"  → {cnt}건 비활성화 완료")
    except Exception as e:
        print(f"  비활성화 오류: {e}")


if __name__ == "__main__":
    k = fetch_kstartup()
    b = fetch_bizinfo()
    deactivate_expired()
    print("=" * 50)
    print(f"전체 완료! K-Startup {k}건 + 기업마당 {b}건")
