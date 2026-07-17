export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const channelKey = process.env.PORTONE_CHANNEL_KEY || '';
  const storeId = process.env.PORTONE_STORE_ID || '';

  if (!channelKey) {
    return res.status(500).json({ error: 'PORTONE_CHANNEL_KEY not configured' });
  }

  return res.status(200).json({
    channelKey,
    storeId,
    testMode: true
  });
}
