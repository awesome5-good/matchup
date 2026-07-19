// api/newsletter.js — 매주 월요일 자동 발송 + 수동 트리거 가능
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;

async function sbFetch(path, options={}) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    ...options,
    headers: {
      'apikey': SUPABASE_SERVICE_KEY,
      'Authorization': `Bearer ${SUPABASE_SERVICE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': options.prefer || '',
      ...(options.headers||{})
    }
  });
  if (!res.ok) throw new Error(`Supabase error: ${res.status} ${await res.text()}`);
  return res.json();
}

export default async function handler(req, res) {
  const auth = req.headers['authorization'] || req.query.secret;
  if (auth !== `Bearer ${process.env.CRON_SECRET}` && auth !== process.env.CRON_SECRET) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  try {
    const subs = await sbFetch('subscribers?is_active=eq.true&select=*');

    if (!subs || subs.length === 0) {
      return res.status(200).json({ message: '구독자 없음' });
    }

    const today = new Date();
    const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
    const todayStr = today.toISOString().split('T')[0];
    const nextWeekStr = nextWeek.toISOString().split('T')[0];
    const programs = await sbFetch(`programs?is_active=eq.true&deadline=gte.${todayStr}&deadline=lte.${nextWeekStr}&order=created_at.desc&limit=5&select=*`);

    const topPrograms = programs?.slice(0, 3) || [];
    let aiComment = '';
    try {
      const claudeRes = await fetch('https://api.anthropic.com/v1/messages', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-api-key': process.env.ANTHROPIC_API_KEY,
          'anthropic-version': '2023-06-01'
        },
        body: JSON.stringify({
          model: 'claude-haiku-4-5',
          max_tokens: 500,
          messages: [{
            role: 'user',
            content: `당신은 소상공인 지원사업 16년 경력 컨설턴트입니다. 아래 이번 주 마감 임박 지원사업 3개를 보고, 소상공인 사장님들에게 보내는 주간 브리핑 코멘트를 작성하세요.

지원사업 목록:
${topPrograms.map((p, i) => `${i+1}. ${p.title} (마감: ${p.deadline}) - ${p.organization}`).join('\n')}

작성 규칙:
- 전체 200자 이내
- 각 사업마다 한 줄 실무 코멘트 (예: "서류보다 면접이 관건", "경쟁률 낮은 지역 공고")
- 딱딱하지 않고 실무자 말투
- 마크다운 금지, 줄바꿈은 \\n 사용`
          }]
        })
      });
      const claudeData = await claudeRes.json();
      aiComment = claudeData.content?.[0]?.text || '';
    } catch (e) {
      aiComment = '이번 주도 좋은 결과 있으시길 바랍니다.';
    }

    const issueNo = Math.ceil((Date.now() - new Date('2026-07-20').getTime()) / (7 * 24 * 60 * 60 * 1000)) || 1;
    let sentCount = 0;

    for (const sub of subs) {
      const html = buildEmailHtml(sub, topPrograms, aiComment, issueNo);
      try {
        await fetch('https://api.resend.com/emails', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${process.env.RESEND_API_KEY}`
          },
          body: JSON.stringify({
            from: 'onboarding@resend.dev',
            to: sub.email,
            subject: `[매치업 ${issueNo}호] 이번 주 놓치면 안 되는 지원사업 ${topPrograms.length}건`,
            html
          })
        });
        sentCount++;
      } catch (e) {
        console.error(`발송 실패: ${sub.email}`, e);
      }
    }

    await sbFetch('newsletter_logs', {
      method: 'POST',
      prefer: 'return=minimal',
      body: JSON.stringify({
        issue_no: issueNo,
        subject: `[매치업 ${issueNo}호] 이번 주 놓치면 안 되는 지원사업 ${topPrograms.length}건`,
        sent_count: sentCount
      })
    });

    return res.status(200).json({ success: true, sent: sentCount, issueNo });

  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: e.message });
  }
}

function buildEmailHtml(sub, programs, aiComment, issueNo) {
  const programRows = programs.map(p => `
    <tr>
      <td style="padding:14px 0;border-bottom:1px solid #f0f0f0;">
        <div style="font-size:16px;font-weight:700;color:#111;margin-bottom:4px;">${p.title}</div>
        <div style="font-size:13px;color:#888;margin-bottom:6px;">${p.organization} · 마감 ${p.deadline}</div>
        <div style="font-size:14px;color:#444;">${(p.description||'').slice(0,80)}...</div>
        <a href="https://matchup-liard.vercel.app" style="display:inline-block;margin-top:8px;font-size:13px;color:#4F46E5;font-weight:600;text-decoration:none;">매치업에서 자격 확인 →</a>
      </td>
    </tr>
  `).join('');

  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f7f7f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:32px 16px;">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
        <tr><td style="background:#4F46E5;border-radius:16px 16px 0 0;padding:28px 32px;">
          <div style="font-size:13px;color:rgba(255,255,255,0.7);margin-bottom:4px;">매치업 레터 ${issueNo}호</div>
          <div style="font-size:22px;font-weight:800;color:#fff;">이번 주 놓치면 안 되는 지원사업</div>
        </td></tr>
        <tr><td style="background:#fff;padding:24px 32px;">
          <div style="background:#EEF2FF;border-radius:12px;padding:16px 20px;margin-bottom:24px;">
            <div style="font-size:12px;font-weight:700;color:#4F46E5;margin-bottom:6px;">오동훈 박사의 이번 주 한마디</div>
            <div style="font-size:14px;color:#333;line-height:1.7;">${aiComment.replace(/\n/g,'<br>')}</div>
          </div>
          <div style="font-size:16px;font-weight:800;color:#111;margin-bottom:4px;">마감 임박 공고 ${programs.length}건</div>
          <div style="font-size:13px;color:#888;margin-bottom:16px;">지금 신청하지 않으면 내년까지 기다려야 합니다</div>
          <table width="100%" cellpadding="0" cellspacing="0">${programRows}</table>
        </td></tr>
        <tr><td style="background:#fff;padding:0 32px 28px;">
          <a href="https://matchup-liard.vercel.app" style="display:block;background:#4F46E5;color:#fff;text-align:center;padding:16px;border-radius:12px;font-size:16px;font-weight:700;text-decoration:none;">내 사업에 맞는 공고 전체 보기 →</a>
        </td></tr>
        <tr><td style="background:#f7f7f8;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;">
          <div style="font-size:12px;color:#aaa;line-height:1.8;">
            브라보경영컨설팅 · 대표 오동훈<br>
            대구광역시 중구 국채보상로 558-1, 2층 A125호<br>
            본 메일은 매치업 서비스 구독 신청 시 발송됩니다.<br>
            <a href="https://matchup-liard.vercel.app/api/unsubscribe?token=${sub.unsubscribe_token}" style="color:#888;">수신 거부</a>
          </div>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>`;
}
