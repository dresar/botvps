const GATEWAY_KEY = 'AR_7651fb06_0f19ac85a3a409b4fe568b2afb7a1512';
const BASE_URL = 'https://one.apprentice.cyou/v1';

async function testAiChat() {
  console.log('🚀 Testing AI Chat Completion (GEMINI)...');

  try {
    const chatRes = await fetch(`${BASE_URL}/chat/completions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${GATEWAY_KEY}` },
      body: JSON.stringify({
        model: 'gemini-2.5-flash',
        messages: [{ role: 'user', content: 'Tes koneksi' }]
      })
    });

    const data = await chatRes.json();
    if (chatRes.ok) {
      console.log('✅ AI Chat Berhasil!');
      console.log('   Balasan AI:', data.choices?.[0]?.message?.content?.trim());
    } else {
      console.error('❌ AI Chat Gagal:', data);
    }
  } catch (err) {
    console.error('❌ Error saat menghubungi API Gateway:', err.message);
  }
}

testAiChat();
