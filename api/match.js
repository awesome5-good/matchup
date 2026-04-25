export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    const body = req.body;
    const company = body.company;
    const programs = body.programs;

    const prompt = `기업 정보: ${company.company_name}, ${company.industry}, ${company.region}
지원사업 목록: ${JSON.stringify(programs.slice(0, 20))}
위 기업에 맞는 TOP 5를 JSON으로만 답변: [{"program_id":"UUID","score":85,"reason":"이유"}]`;

    const claudeRes = await fetch('https://api.anthropic.com/v1/messages', {
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

    const claudeData = await claudeRes.json();
    
    if (!claudeData.content || !claudeData.content[0]) {
      return res.status(500).json({ error: 'Claude 오류', detail: claudeData });
    }

    const text = claudeData.content[0].text.trim();
    let matches;
    try {
      matches = JSON.parse(text);
    } catch {
      const m = text.match(/\[[\s\S]*\]/);
      matches = m ? JSON.parse(m[0]) : [];
    }

    return res.status(200).json({ matches });

  } catch (err) {
    return res.status(500).json({ error: err.message, stack: err.stack });
  }
}