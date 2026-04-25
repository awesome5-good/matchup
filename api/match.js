export const config = { api: { bodyParser: true } };

export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const { company, programs } = req.body;

    if (!company || !programs) {
      return res.status(400).json({ error: 'company and programs required' });
    }

    const prompt = `당신은 정부 지원사업 매칭 전문가입니다.

## 기업 정보
- 기업명: ${company.company_name}
- 업종: ${company.industry} (${company.industry_detail || ''})
- 지역: ${company.region} ${company.district || ''}
- 직원수: ${company.employee_count || '미상'}명
- 연매출: ${company.annual_revenue || '미상'}만원
- 기업소개: ${company.description || '없음'}

## 지원사업 목록 (${programs.length}건)
${JSON.stringify(programs)}

## 지시사항
위 기업에 가장 적합한 지원사업 TOP 5를 선정하고, 각각 매칭 점수(0-100)와 이유를 JSON으로만 답변하세요.
다른 텍스트 없이 아래 형식으로만:
[{"program_id":"UUID","score":85,"reason":"매칭 이유 한 문장"}]`;

    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': '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',
        'anthropic-version': '2023-06-01'
      },
      body: JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 1000,
        messages: [{ role: 'user', content: prompt }]
      })
    });

    const data = await response.json();
    console.log('Claude 응답:', JSON.stringify(data));
    
    if (!data.content || !data.content[0]) {
      return res.status(500).json({ error: 'Claude API 응답 오류', data });
    }

    const text = data.content[0].text.trim();
    
    let matches;
    try {
      matches = JSON.parse(text);
    } catch {
      const jsonMatch = text.match(/\[[\s\S]*\]/);
      if (jsonMatch) {
        matches = JSON.parse(jsonMatch[0]);
      } else {
        return res.status(500).json({ error: '파싱 오류', raw: text });
      }
    }

    return res.status(200).json({ matches });

  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
}