import anthropic
from supabase import create_client
import json

SUPABASE_URL = "https://wykupodtnbcrebgbzyxr.supabase.co"
SUPABASE_KEY = "sb_publishable_THekjy2-GusHmZ7FrjX9UQ_gm41EUr2"
CLAUDE_API_KEY = "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"

db = create_client(SUPABASE_URL, SUPABASE_KEY)
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)

def ai_match(company_id):
    # 기업 정보 가져오기
    company = db.table("companies").select("*").eq("id", company_id).single().execute().data
    if not company:
        print("기업 없음")
        return

    print(f"기업: {company['company_name']} ({company['industry']}, {company['region']})")

    # 지원사업 목록 가져오기
    programs = db.table("programs").select("*").eq("is_active", True).execute().data
    print(f"지원사업 {len(programs)}건 분석 중...")

    # 프로그램 요약 목록 만들기
    program_list = []
    for p in programs:
        program_list.append({
            "id": p["id"],
            "title": p["title"],
            "organization": p.get("organization", ""),
            "category": p.get("category", ""),
            "eligibility": p.get("eligibility", "")[:200] if p.get("eligibility") else "",
            "deadline": p.get("deadline", "")
        })

    # Claude에게 매칭 요청
    prompt = f"""
당신은 정부 지원사업 매칭 전문가입니다.

## 기업 정보
- 기업명: {company['company_name']}
- 업종: {company['industry']} ({company.get('industry_detail', '')})
- 지역: {company['region']} {company.get('district', '')}
- 직원수: {company.get('employee_count', '미상')}명
- 연매출: {company.get('annual_revenue', '미상')}만원
- 기업소개: {company.get('description', '없음')}

## 지원사업 목록
{json.dumps(program_list, ensure_ascii=False, indent=2)}

## 지시사항
위 기업에 가장 적합한 지원사업 TOP 5를 선정하고, 각각 매칭 점수(0-100)와 이유를 JSON으로만 답변하세요.

반드시 아래 형식으로만 답변하세요:
[
  {{
    "program_id": "UUID",
    "score": 85,
    "reason": "매칭 이유 한 문장"
  }}
]
"""

    print("Claude AI 분석 중...")
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    result_text = response.content[0].text.strip()
    
    # JSON 파싱
    try:
        matches = json.loads(result_text)
    except:
        # JSON 추출 시도
        import re
        json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
        if json_match:
            matches = json.loads(json_match.group())
        else:
            print("파싱 오류:", result_text)
            return

    print(f"\nAI 매칭 결과 TOP {len(matches)}:")
    
    # 기존 매칭 삭제 후 새로 저장
    db.table("matches").delete().eq("company_id", company_id).execute()
    
    for m in matches:
        prog = next((p for p in programs if p["id"] == m["program_id"]), None)
        if prog:
            db.table("matches").insert({
                "company_id": company_id,
                "program_id": m["program_id"],
                "match_score": m["score"],
                "match_reason": m["reason"]
            }).execute()
            print(f"✅ {m['score']}점 - {prog['title'][:40]}")
            print(f"   이유: {m['reason']}")

    print(f"\n완료! {len(matches)}건 AI 매칭 저장됨")

# 가장 최근 기업으로 테스트
latest = db.table("companies").select("*").order("created_at", desc=True).limit(1).execute().data
if latest:
    ai_match(latest[0]["id"])