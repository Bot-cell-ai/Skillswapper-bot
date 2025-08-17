# web.py
import os
import json
from flask import Flask, request, Response

app = Flask(__name__)

# Load client config once from secret
CLIENT_CONFIG = json.loads(os.environ["FIREBASE_CLIENT_CONFIG_JSON"])

CHAT_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>SkillSwapper Chat</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root {
      --bg: #ECE5DD;
      --header: #075E54;
      --header-accent: #128C7E;
      --bubble-me: #DCF8C6;
      --bubble-other: #FFFFFF;
      --text-muted: #667781;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, -apple-system, Arial, sans-serif; background: var(--bg); height: 100vh; display: flex; flex-direction: column; }
    #chat-header {
      background: var(--header);
      color: #fff; padding: 12px 16px; display: flex; align-items: center; gap: 10px;
      position: sticky; top: 0; z-index: 1;
    }
    #room-title { font-weight: 700; font-size: 16px; line-height: 1.2; }
    #room-sub { font-size: 12px; opacity: .9; }
    #chat-box {
      flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px;
      background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="160" height="160" viewBox="0 0 160 160"><rect width="160" height="160" fill="%23ECE5DD"/></svg>') repeat;
    }
    .row { display: flex; }
    .msg {
      max-width: 75%; padding: 8px 12px; border-radius: 12px; font-size: 14px; line-height: 1.35;
      box-shadow: 0 1px 0 rgba(0,0,0,.05); position: relative; white-space: pre-wrap; word-break: break-word;
    }
    .me   { align-self: flex-end; justify-content: flex-end; }
    .me .msg    { background: var(--bubble-me); border-top-right-radius: 4px; }
    .other { align-self: flex-start; justify-content: flex-start; }
    .other .msg { background: var(--bubble-other); border-top-left-radius: 4px; }
    .meta { display:block; margin-top: 4px; font-size: 11px; color: var(--text-muted); text-align: right; }
    #composer-wrap {
      position: sticky; bottom: 0; background: #F0F2F5; padding: 10px; border-top: 1px solid #ddd;
      display: flex; gap: 8px;
    }
    #msg { flex: 1; padding: 12px; border: 1px solid #ccc; border-radius: 20px; background: #fff; }
    #sendBtn {
      padding: 10px 16px; background: var(--header-accent); color: #fff; border: none; border-radius: 18px; cursor: pointer;
    }
    #expired {
      display: none; background: #ffefef; color: #a30000; padding: 8px 12px; text-align: center; font-size: 14px; border-bottom: 1px solid #f1c6c6;
    }
  </style>
</head>
<body>
  <div id="expired">This chat has expired.</div>
  <div id="chat-header">
    <div>
      <div id="room-title">SkillSwapper</div>
      <div id="room-sub"></div>
    </div>
  </div>

  <div id="chat-box"></div>

  <div id="composer-wrap">
    <input id="msg" type="text" placeholder="Type a message" />
    <button id="sendBtn">Send</button>
  </div>

  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-database-compat.js"></script>
  <script>
    // Firebase init
    const FIREBASE_CONFIG = %CLIENT_CONFIG%;
    firebase.initializeApp(FIREBASE_CONFIG);
    const db = firebase.database();

    // Helpers
    const qp = (k) => new URLSearchParams(location.search).get(k) || "";
    const roomId   = qp('room');
    const meId     = qp('me');
    const myNameQ  = decodeURIComponent(qp('myName') || '');
    const peerNameQ= decodeURIComponent(qp('peerName') || '');

    const box   = document.getElementById('chat-box');
    const input = document.getElementById('msg');
    const send  = document.getElementById('sendBtn');
    const title = document.getElementById('room-title');
    const sub   = document.getElementById('room-sub');
    const expiredBar = document.getElementById('expired');

    let myName = myNameQ || 'Me';
    let peerName = peerNameQ || 'Peer';

    function disableComposer(disabled) {
      input.disabled = disabled; send.disabled = disabled;
    }

    function addBubble(isMe, name, text, timeMs) {
      const row = document.createElement('div');
      row.className = isMe ? 'row me' : 'row other';

      const bubble = document.createElement('div');
      bubble.className = 'msg';
      const ts = timeMs ? new Date(timeMs).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) : '';
      bubble.innerHTML = `<strong>${name}</strong><br>${text}<span class="meta">${ts}</span>`;
      row.appendChild(bubble);
      box.appendChild(row);
      box.scrollTop = box.scrollHeight;
    }

    async function init() {
      if (!roomId) {
        title.textContent = 'No room specified';
        sub.textContent = '';
        disableComposer(true);
        return;
      }

      // Read room once to get names + expiry
      const roomRef = db.ref('chats/' + roomId);
      const snap = await roomRef.get();
      if (!snap.exists()) {
        title.textContent = 'Chat not found';
        disableComposer(true);
        expiredBar.style.display = 'block';
        return;
      }
      const data = snap.val();

      // Resolve names from DB if query params missing
      if (!myNameQ || !peerNameQ) {
        try {
          const users = data.users || {};
          const meNode   = users[meId] || {};
          const peerId   = Object.keys(users).find(uid => uid !== meId) || '';
          const peerNode = users[peerId] || {};
          myName   = myNameQ   || (meNode.name || ('Me ' + meId));
          peerName = peerNameQ || (peerNode.name || 'Peer');
        } catch (e) {
          // ignore
        }
      }

      // Header
      title.textContent = `${myName} ↔ ${peerName}`;
      sub.textContent = `Room: ${roomId}`;

      // Check expiry
      const expired = data.expires_at && (Date.now() > new Date(data.expires_at).getTime());
      if (expired) {
        expiredBar.style.display = 'block';
        disableComposer(true);
      }

      // Load history then subscribe
      const messagesRef = db.ref('chats/' + roomId + '/messages');

      // history
      const hist = await messagesRef.get();
      if (hist.exists()) {
        const items = Object.values(hist.val()).sort((a,b)=> (a.time||0)-(b.time||0));
        for (const m of items) {
          addBubble(String(m.senderId) === String(meId), m.sender || 'User', m.text || '', m.time || Date.now());
        }
      }

      // live updates
      messagesRef.on('child_added', (snap) => {
        const m = snap.val();
        if (!m) return;
        addBubble(String(m.senderId) === String(meId), m.sender || 'User', m.text || '', m.time || Date.now());
      });

      // send
      const doSend = () => {
        const text = (input.value || '').trim();
        if (!text) return;
        const msgRef = messagesRef.push();
        msgRef.set({
          text,
          time: Date.now(),
          sender: myName,
          senderId: meId || 'anon'
        });
        input.value = '';
      };

      send.onclick = doSend;
      input.onkeyup = (e) => { if (e.key === 'Enter') doSend(); };
    }

    init();
  </script>
</body>
</html>
"""

@app.route("/chat")
def chat_page():
    html = CHAT_HTML.replace("%CLIENT_CONFIG%", json.dumps(CLIENT_CONFIG))
    return Response(html, mimetype="text/html")

def start_web(host="0.0.0.0", port=8000):
    app.run(host=host, port=port)