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
