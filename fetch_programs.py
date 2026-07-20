# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
매치업 지원사업 데이터 수집 v3
소스별 수집 결과 및 오류를 자가진단 리포트로 출력

[소스 목록]
1. K-Startup (창업진흥원)           — 기존
2. 기업마당 (Bizinfo)               — 기존
3. 중소벤처기업부 공고 조회 서비스   — 신규 (공공데이터포털 키)
4. 중소벤처24 공고정보               — 신규 (portal.smes.go.kr 키)
5. 온통청년 청년정책API              — 키 입력 시 자동 활성화

실행: python fetch_programs.py
"""
import requests
from datetime import date
from supabase import create_client

# ── 인증키 ──────────────────────────────────────────
SUPABASE_URL = "https://wykupodtnbcrebgbzyxr.supabase.co"
SUPABASE_KEY = "sb_publishable_THekjy2-GusHmZ7FrjX9UQ_gm41EUr2"

KSTARTUP_KEY   = "4f518baf8a28ed0f517bba932b36bc8dccb2b3c5c5b16993de091777e0f48ef4"
BIZINFO_KEY    = "2I57xn"
DATA_GO_KEY    = "4f518baf8a28ed0f517bba932b36bc8dccb2b3c5c5b16993de091777e0f48ef4"  # 공공데이터포털
SMES24_KEY     = "wQZe2AZiStdLNDd4um8dHnWQviVTRAZxv1jV+EyGcrXpc5y3+e3eHjtgn32Psfo0fr8tTUZ22JYPAxrcN+igjw=="
YOUTH_KEY      = "ba5d58dc-e47f-4de8-8ce3-e55f51637f0a"
# ────────────────────────────────────────────────────

db    = create_client(SUPABASE_URL, SUPABASE_KEY)
today = date.today().isoformat()

# 소스별 결과 집계
report = {}


def fmt_date(s):
    if not s:
        return None
    s = str(s).strip().replace(".", "-").replace("/", "-")
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s
    return None


def upsert_program(program):
    try:
        db.table("programs").upsert(program, on_conflict="title").execute()
        return True
    except Exception as e:
        print(f"  upsert 오류: {e}")
        return False


# ══════════════════════════════════════════
# 1. K-Startup
# ══════════════════════════════════════════
def fetch_kstartup():
    src = "K-Startup"
    print(f"\n{'='*50}")
    print(f"[1/5] {src} 수집 시작")
    url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
    total, errors = 0, 0
    for page in range(1, 6):
        try:
            res  = requests.get(url, params={"serviceKey": KSTARTUP_KEY, "page": page, "perPage": 100, "returnType": "JSON"}, timeout=15)
            data = res.json()
        except Exception as e:
            print(f"  페이지 {page} 호출 실패: {e}")
            errors += 1
            break
        items = data.get("data", [])
        if not items:
            break
        print(f"  페이지 {page}: {len(items)}건 수신")
        for item in items:
            title    = (item.get("biz_pbanc_nm") or "").strip()
            if not title:
                continue
            deadline = fmt_date(item.get("pbanc_rcpt_end_dt"))
            if deadline and deadline < today:
                continue
            category = item.get("supt_biz_clsfc", "") or "창업"
            region   = item.get("supt_regin", "") or ""
            tags     = ["K-Startup", category]
            if region:
                tags.append(region)
            if upsert_program({"title": title, "organization": item.get("pbanc_ntrp_nm",""), "category": category,
                               "description": item.get("pbanc_ctnt",""), "deadline": deadline,
                               "eligibility": item.get("aply_trgt_ctnt",""), "source_url": item.get("detl_pg_url",""),
                               "tags": tags, "is_active": True}):
                total += 1
    report[src] = {"saved": total, "errors": errors}
    print(f"  → {src} 완료: {total}건 저장/갱신" + (f" | 오류 {errors}건 [경고]" if errors else ""))
    return total


# ══════════════════════════════════════════
# 2. 기업마당 (Bizinfo)
# ══════════════════════════════════════════
def fetch_bizinfo():
    src = "기업마당"
    print(f"\n{'='*50}")
    if not BIZINFO_KEY:
        print(f"[2/5] {src} — 인증키 미입력, 건너뜀")
        report[src] = {"saved": 0, "errors": 0, "skipped": True}
        return 0
    print(f"[2/5] {src} 수집 시작")
    url    = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    total, errors = 0, 0
    try:
        res   = requests.get(url, params={"crtfcKey": BIZINFO_KEY, "dataType": "json", "searchCnt": "300"}, timeout=20)
        data  = res.json()
        items = data.get("jsonArray", []) or data.get("item", []) or []
        print(f"  {len(items)}건 수신")
        for item in items:
            title = (item.get("pblancNm") or "").strip()
            if not title:
                continue
            period   = item.get("reqstBeginEndDe", "") or ""
            deadline = fmt_date(period.split("~")[-1].strip()) if "~" in period else None
            if deadline and deadline < today:
                continue
            category = item.get("pldirSportRealmLclasCodeNm", "") or "경영"
            organ    = item.get("jrsdInsttNm", "") or item.get("excInsttNm", "")
            detail_url = item.get("pblancUrl", "") or ""
            if detail_url.startswith("/"):
                detail_url = "https://www.bizinfo.go.kr" + detail_url
            if upsert_program({"title": title, "organization": organ, "category": category,
                               "description": (item.get("bsnsSumryCn") or "")[:2000], "deadline": deadline,
                               "eligibility": item.get("trgetNm", "") or "", "source_url": detail_url,
                               "tags": ["기업마당", category], "is_active": True}):
                total += 1
    except Exception as e:
        print(f"  호출 실패: {e}")
        errors += 1
    report[src] = {"saved": total, "errors": errors}
    print(f"  → {src} 완료: {total}건 저장/갱신" + (f" | 오류 {errors}건 [경고]" if errors else ""))
    return total


# ══════════════════════════════════════════
# 3. 중소벤처기업부 공고 조회 서비스 (공공데이터포털)
# ══════════════════════════════════════════
def fetch_mss():
    src = "중소벤처기업부"
    print(f"\n{'='*50}")
    print(f"[3/5] {src} 공고 조회 서비스 수집 시작")
    url   = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
    total, errors = 0, 0
    for page in range(1, 6):
        try:
            res  = requests.get(url, params={"crtfcKey": DATA_GO_KEY, "dataType": "json", "searchCnt": "100", "pageIndex": page}, timeout=15)
            if res.status_code != 200:
                print(f"  페이지 {page}: HTTP {res.status_code}")
                errors += 1
                break
            data = res.json()
        except Exception as e:
            print(f"  페이지 {page} 호출 실패: {e}")
            errors += 1
            break
        items = data.get("jsonArray", []) or []
        if not items:
            print(f"  페이지 {page}: 데이터 없음")
            break

        for item in items:
            title = (item.get("pblancNm") or "").strip()
            if not title:
                continue
            period   = item.get("reqstBeginEndDe", "") or ""
            deadline = fmt_date(period.split("~")[-1].strip()) if "~" in period else None
            if deadline and deadline < today:
                continue
            category = item.get("pldirSportRealmLclasCodeNm", "") or "경영"
            organ    = item.get("jrsdInsttNm", "") or item.get("excInsttNm", "")
            detail_url = item.get("pblancUrl", "") or ""
            if detail_url.startswith("/"):
                detail_url = "https://www.bizinfo.go.kr" + detail_url
            if upsert_program({"title": title, "organization": organ, "category": category,
                               "description": (item.get("bsnsSumryCn") or "")[:2000], "deadline": deadline,
                               "eligibility": item.get("trgetNm", "") or "", "source_url": detail_url,
                               "tags": ["중소벤처기업부", category], "is_active": True}):
                total += 1
        continue
    report[src] = {"saved": total, "errors": errors}
    print(f"  → {src} 완료: {total}건 저장/갱신" + (f" | 오류 {errors}건 [경고]" if errors else ""))
    return total


# ══════════════════════════════════════════
# 4. 중소벤처24 공고정보
# ══════════════════════════════════════════
def fetch_smes24():
    src = "중소벤처24"
    print(f"\n{'='*50}")
    print(f"[3/4] {src} 공고정보 수집 시작")
    url   = "https://www.smes.go.kr/fnct/apiReqst/extPblancInfo"
    token = "wQZe2AZiStdLNDd4um8dHnWQviVTRAZxv1jV+EyGcrXpc5y3+e3eHjtgn32Psfo0fr8tTUZ22JYPAxrcN+igjw=="
    total, errors = 0, 0
    try:
        import urllib.parse
        from datetime import datetime, timedelta
        encoded_token = urllib.parse.quote(token, safe='')
        all_items = []
        # 3개월씩 분할 요청 (전체를 한 번에 받으면 타임아웃)
        base = datetime.today()
        periods = [
            (base - timedelta(days=90), base),
            (base, base + timedelta(days=90)),
            (base + timedelta(days=90), base + timedelta(days=180)),
        ]
        for start, end in periods:
            strDt = start.strftime("%Y%m%d")
            endDt = end.strftime("%Y%m%d")
            try:
                r = requests.get(
                    f"{url}?token={encoded_token}&html=no&strDt={strDt}&endDt={endDt}",
                    timeout=60
                )
                if r.status_code != 200:
                    print(f"  HTTP {r.status_code} ({strDt}~{endDt})")
                    continue
                d = r.json()
                if d.get("resultCd") != "0":
                    print(f"  API 오류: {d.get('resultMsg','')} ({strDt}~{endDt})")
                    continue
                chunk = d.get("data", [])
                print(f"  {strDt}~{endDt}: {len(chunk)}건 수신")
                all_items.extend(chunk)
            except Exception as e:
                print(f"  구간 {strDt}~{endDt} 실패: {e}")
                errors += 1
        # 중복 제거 (pblancSeq 기준)
        seen = set()
        items = []
        for item in all_items:
            seq = item.get("pblancSeq")
            if seq not in seen:
                seen.add(seq)
                items.append(item)
        print(f"  총 {len(items)}건 (중복 제거 후)")
        for item in items:
            title = (item.get("pblancNm") or "").strip()
            if not title:
                continue
            deadline = fmt_date(item.get("pblancEndDt"))
            if deadline and deadline < today:
                continue
            # 자격 조건을 구조화해서 eligibility에 저장
            elig_parts = []
            if item.get("cmpScale"):
                elig_parts.append(f"기업규모: {item.get('cmpScale')}")
            if item.get("ablbiz"):
                elig_parts.append(f"업력: {item.get('ablbiz')}")
            if item.get("emplyCnt"):
                elig_parts.append(f"종업원수: {item.get('emplyCnt')}")
            if item.get("areaNm"):
                elig_parts.append(f"지역: {item.get('areaNm')}")
            if item.get("fntnYn") == "Y":
                elig_parts.append("예비창업자 가능")
            if item.get("refntnYn") == "Y":
                elig_parts.append("재창업 가능")
            raw_trget = (item.get("sportTrget") or "")
            if raw_trget:
                elig_parts.insert(0, raw_trget[:200])
            eligibility = " | ".join(elig_parts)
            category = item.get("bizType") or "경영"
            organ    = item.get("sportInsttNm") or ""
            detail_url = item.get("pblancDtlUrl") or item.get("reqstLinkInfo") or ""
            description = " ".join(filter(None, [
                item.get("policyCnts") or "",
                item.get("sportCnts") or ""
            ]))[:2000]
            tags = ["중소벤처24", category]
            if item.get("areaNm"):
                tags.append(item.get("areaNm"))
            if upsert_program({"title": title, "organization": organ, "category": category,
                               "description": description, "deadline": deadline,
                               "eligibility": eligibility, "source_url": detail_url,
                               "tags": tags, "is_active": True}):
                total += 1
    except Exception as e:
        print(f"  호출 실패: {e}")
        errors += 1
    report[src] = {"saved": total, "errors": errors}
    print(f"  -> {src} 완료: {total}건 저장/갱신" + (f" | 오류 {errors}건" if errors else ""))
    return total


# ══════════════════════════════════════════
# 5. 온통청년 청년정책API
# ══════════════════════════════════════════
def fetch_youth():
    src = "온통청년"
    print(f"\n{'='*50}")
    if not YOUTH_KEY:
        print(f"[4/4] {src} - 인증키 미입력 (승인 대기 중), 건너뜀")
        report[src] = {"saved": 0, "errors": 0, "skipped": True}
        return 0
    print(f"[4/4] {src} 수집 시작")
    url   = "https://www.youthcenter.go.kr/go/ythip/getPlcy"
    total, errors = 0, 0
    for page in range(1, 11):  # 최대 10페이지
        try:
            res  = requests.get(url, params={"apiKeyNm": YOUTH_KEY, "pageNum": page, "pageSize": 100, "rtnType": "json"}, timeout=15)
            data = res.json()
        except Exception as e:
            print(f"  페이지 {page} 호출 실패: {e}")
            errors += 1
            break
        result = data.get("result", data)
        items = result.get("youthPolicyList", [])
        if not items:
            break
        print(f"  페이지 {page}: {len(items)}건 수신")
        for item in items:
            title    = (item.get("plcyNm") or "").strip()
            if not title:
                continue
            # 사업기간 종료일 → deadline
            deadline = fmt_date(item.get("bizPrdEndYmd"))
            if deadline and deadline < today:
                continue
            eligibility = " | ".join(filter(None, [
                item.get("addAplyQlfcCndCn", ""),
                f"연령: {item.get('sprtTrgtMinAge','')}~{item.get('sprtTrgtMaxAge','')}세" if item.get("sprtTrgtAgeLmtYn") == "Y" else "",
                item.get("ptcpPrpTrgtCn", "")
            ]))
            detail_url = item.get("aplyUrlAddr") or item.get("refUrlAddr1", "")
            category   = item.get("lclsfNm", "청년")
            if upsert_program({"title": title, "organization": item.get("sprvsnInstCdNm", ""),
                               "category": category, "description": (item.get("plcyExplnCn") or "")[:2000],
                               "deadline": deadline, "eligibility": eligibility,
                               "source_url": detail_url, "tags": ["온통청년", category], "is_active": True}):
                total += 1
    report[src] = {"saved": total, "errors": errors}
    print(f"  → {src} 완료: {total}건 저장/갱신" + (f" | 오류 {errors}건 [경고]" if errors else ""))
    return total


# ══════════════════════════════════════════
# 마감 공고 비활성화
# ══════════════════════════════════════════
def deactivate_expired():
    print(f"\n{'='*50}")
    print("[정리] 마감 지난 공고 비활성화")
    try:
        res = db.table("programs").update({"is_active": False}).lt("deadline", today).eq("is_active", True).execute()
        cnt = len(res.data) if res.data else 0
        print(f"  → {cnt}건 비활성화 완료")
        return cnt
    except Exception as e:
        print(f"  비활성화 오류: {e}")
        return 0


# ══════════════════════════════════════════
# 자가진단 리포트
# ══════════════════════════════════════════
def print_report(deactivated):
    print(f"\n{'='*50}")
    print("수집 결과 리포트")
    print(f"{'='*50}")
    total_saved = 0
    for src, r in report.items():
        if r.get("skipped"):
            status = "[건너뜀]  건너뜀 (키 미입력)"
        elif r.get("errors", 0) > 0:
            status = f"[경고]  저장 {r['saved']}건 | 오류 {r['errors']}건 — 사이트 개편 가능성, 확인 필요"
        elif r["saved"] == 0:
            status = f"[오류] 0건 — API 응답 확인 필요"
        else:
            status = f"[OK] {r['saved']}건 저장/갱신"
        print(f"  {src:<12} : {status}")
        total_saved += r.get("saved", 0)
    print(f"{'─'*50}")
    print(f"  전체 저장/갱신  : {total_saved}건")
    print(f"  마감 비활성화   : {deactivated}건")
    print(f"{'='*50}")


if __name__ == "__main__":
    k = fetch_kstartup()
    b = fetch_bizinfo()
    s = fetch_smes24()
    y = fetch_youth()
    d = deactivate_expired()
    print_report(d)
