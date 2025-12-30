document.querySelectorAll('.word').forEach(span => {
  span.addEventListener('click', async (e) => {
    const word = e.target.textContent.replace(/[^a-zA-Z]/g, '');
    if (!word) return;
    const res = await fetch('/api/lookup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({word})
    });
    const data = await res.json();
    document.getElementById('popupWord').innerText = data.word;
    document.getElementById('popupMeaning').innerText = data.meaning;
    document.getElementById('popup').classList.remove('hidden');
    document.getElementById('addBtn').onclick = () => addWord(data.word, data.meaning);
  });
});

function closePopup() {
  document.getElementById('popup').classList.add('hidden');
}

async function addWord(word, meaning) {
  const res = await fetch('/api/add_word', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({word, meaning, text_id: textId, text_title: textTitle})
  });
  const data = await res.json();
  alert(data.message);
  closePopup();
}
<script>
function submitBulkWords() {
  const textId = document.getElementById('wordTextSelect').value;
  if (!textId) return alert('텍스트를 선택하세요.');

  const raw = document.getElementById('bulkWordInput').value.trim();
  if (!raw) return alert('단어 목록을 입력하세요.');

  // ✅ 각 줄을 "탭" 또는 "공백" 기준으로 분리
  const lines = raw.split('\n').filter(line => line.trim());
  const words = [];

  lines.forEach(line => {
    // 탭(\t) 또는 여러 공백으로 구분
    const parts = line.split(/\t+|\s{2,}/);
    const word = parts[0]?.trim();
    const meaning = parts.slice(1).join(' ').trim();
    if (word && meaning) words.push({ word, meaning });
  });

  if (words.length === 0) return alert('단어/뜻 형식을 확인해주세요.');

  fetch('/upload_words', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text_id: textId, words })
  })
  .then(res => res.json())
  .then(() => {
    alert(`✅ ${words.length}개 단어 업로드 완료`);
    closeUploadModal();
    location.reload();
  })
  .catch(() => alert('❌ 업로드 중 오류 발생'));
}
</script>
