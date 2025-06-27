document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function(e) {
  if (e.key === 'Enter') sendMessage();
});

function appendMessage(text, sender) {
  const chatBox = document.getElementById('chat-box');
  const bubble = document.createElement('div');
  bubble.className = sender;
  bubble.textContent = text;
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const msg = input.value.trim();
  if (!msg) return;
  appendMessage(msg, 'user');
  input.value = '';
  appendMessage('Thinking...', 'bot');

  try {
    const res = await fetch('/suggestions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg })
    });
    const data = await res.json();
    // remove 'Thinking...'
    document.getElementById('chat-box').lastChild.remove();
    data.suggestions.forEach(item => {
      appendMessage(item.title + ': ' + item.description, 'bot');
    });
  } catch (err) {
    console.error(err);
  }
}