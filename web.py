# web.py
import os
import json
from flask import Flask, Response

app = Flask(__name__)

# Load client config once from secret
CLIENT_CONFIG = json.loads(os.environ["FIREBASE_CLIENT_CONFIG_JSON"])

CHAT_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>SkillSwapper Chat</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root{
      --bg:#F4F6F9;
      --header:#3F51B5;            /* deep indigo */
      --me-start:#26C6DA;          /* teal → blue gradient */
      --me-end:#29B6F6;
      --peer-start:#FFCC80;        /* peach → coral gradient */
      --peer-end:#FF8A65;
      --text:#1f2937;
      --muted:#6b7280;
      --bubble-shadow:0 8px 20px rgba(0,0,0,0.08);
      --input-bg:#fff;
      --send-bg:#3F51B5;
      --send-bg-hover:#34449c;
      --border:#e5e7eb;
    }

    *{box-sizing:border-box}
    body{
      margin:0;
      background:var(--bg);
      font-family:'Inter', system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
      color:var(--text);
      height:100dvh;
      display:flex;
      flex-direction:column;
    }

    /* Header */
    .header{
      position:sticky; top:0; z-index:10;
      display:flex; align-items:center; gap:12px;
      padding:12px 14px;
      background:var(--header);
      color:#fff;
      box-shadow:0 2px 12px rgba(0,0,0,0.15);
    }
    .avatar{
      width:40px; height:40px; border-radius:50%;
      display:grid; place-items:center;
      font-weight:700; color:#fff; flex:0 0 auto;
      box-shadow:0 2px 6px rgba(0,0,0,0.15);
    }
    .title{
      display:flex; flex-direction:column; line-height:1.15;
    }
    .title .name{font-weight:700; font-size:16px}
    .title .status{font-size:12px; opacity:.9}

    /* Chat area */
    .chat{
      flex:1; overflow:auto; padding:14px 12px 12px;
      background:
        radial-gradient(12px 12px at 12px 12px, rgba(0,0,0,0.015), transparent 60%) repeat,
        var(--bg);
      background-size:24px 24px;
    }
    .group{display:flex; gap:10px; align-items:flex-end; margin:8px 0;}
    .group.me{justify-content:flex-end}
    .bubble{
      max-width:min(76%, 720px);
      padding:10px 12px;
      border-radius:16px;
      background:#fff;
      box-shadow:var(--bubble-shadow);
      position:relative;
      display:flex; flex-direction:column; gap:6px;
      word-wrap:break-word; white-space:pre-wrap;
    }
    .bubble.me{
      background:linear-gradient(145deg, var(--me-start), var(--me-end));
      color:#053041;
    }
    .bubble.peer{
      background:linear-gradient(145deg, var(--peer-start), var(--peer-end));
      color:#5b2b1e;
    }
    .meta{
      display:flex; gap:8px; align-items:center; justify-content:flex-end;
      font-size:11px; opacity:.8;
    }
    .meta .ticks{font-weight:700}
    .time{opacity:.9}
    .msg-text{font-size:14px}

    /* Input bar */
    .composer{
      position:sticky; bottom:0; z-index:10;
      background:linear-gradient(180deg, rgba(244,246,249,0.6), var(--bg));
      padding:10px 10px;
      border-top:1px solid var(--border);
      display:flex; gap:8px; align-items:center;
    }
    .input{
      flex:1; background:var(--input-bg);
      border:1px solid var(--border);
      border-radius:14px; padding:12px;
      font-size:14px; outline:none;
      box-shadow:0 1px 2px rgba(0,0,0,0.04) inset;
    }
    .send{
      border:none; padding:12px 16px;
      background:var(--send-bg); color:#fff;
      border-radius:12px; cursor:pointer; font-weight:700;
      transition:.15s ease-in-out;
      box-shadow:0 6px 14px rgba(63,81,181,0.25);
    }
    .send:hover{ background:var(--send-bg-hover) }

    /* Ads (optional) */
    .ad{ margin:6px 10px; border:1px dashed var(--border); color:var(--muted);
         border-radius:12px; padding:10px; text-align:center; font-size:13px; }

    /* Utility */
    .hidden{display:none}
  </style>
</head>
<body>
  <!-- Top ad slot (optional) -->
  <div class="ad" id="ad-top"><em>Ad slot</em></div>

  <!-- Header -->
  <div class="header">
    <div id="peerAvatar" class="avatar">?</div>
    <div class="title">
      <div class="name" id="peerNameEl">Chat</div>
      <div class="status" id="statusEl">Connecting…</div>
    </div>
  </div>

  <!-- Chat area -->
  <div class="chat" id="chat"></div>

  <!-- Composer -->
  <div class="composer">
    <input id="msg" class="input" type="text" placeholder="Type a message"/>
    <button id="sendBtn" class="send">Send</button>
  </div>

  <!-- Bottom ad slot (optional) -->
  <div class="ad" id="ad-bottom"><em>Ad slot</em></div>

  <!-- Firebase -->
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-app-compat.js"></script>
  <script src="https://www.gstatic.com/firebasejs/9.22.1/firebase-database-compat.js"></script>
  <script>
    // --- Setup
    const FIREBASE_CONFIG = %CLIENT_CONFIG%;
    firebase.initializeApp(FIREBASE_CONFIG);
    const db = firebase.database();

    // --- Helpers
    const qs = new URLSearchParams(location.search);
    const roomId   = qs.get('room');
    const myId     = qs.get('me') || '';
    const peerId   = qs.get('peer') || '';
    const myName   = qs.get('myName')   ? decodeURIComponent(qs.get('myName'))   : 'Me';
    const peerName = qs.get('peerName') ? decodeURIComponent(qs.get('peerName')) : 'Partner';

    const chatEl   = document.getElementById('chat');
    const inputEl  = document.getElementById('msg');
    const sendBtn  = document.getElementById('sendBtn');
    const statusEl = document.getElementById('statusEl');
    const peerNameEl = document.getElementById('peerNameEl');
    const peerAvatarEl = document.getElementById('peerAvatar');

    function initials(name){
      if(!name) return '?';
      const parts = name.trim().split(/\s+/);
      const first = parts[0]?.[0] || '';
      const second = parts.length > 1 ? parts[1][0] : '';
      return (first + second).toUpperCase();
    }
    function colorFromName(name){
      // consistent pastel for avatar
      let h = 0;
      for (let i=0;i<name.length;i++){ h = (h*31 + name.charCodeAt(i))>>>0; }
      const hue = h % 360;
      return `hsl(${hue} 70% 45%)`;
    }
    function fmtTime(ms){
      const d = new Date(ms);
      return d.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    }
    function atBottom(){
      return chatEl.scrollHeight - chatEl.scrollTop - chatEl.clientHeight < 20;
    }
    function scrollToBottom(){
      chatEl.scrollTo({top: chatEl.scrollHeight, behavior: 'smooth'});
    }

    // UI header
    peerNameEl.textContent = peerName;
    peerAvatarEl.textContent = initials(peerName);
    peerAvatarEl.style.background = colorFromName(peerName);

    if(!roomId){
      chatEl.innerHTML = '<div class="group"><div class="bubble">No room specified.</div></div>';
      inputEl.disabled = true; sendBtn.disabled = true;
    }else{
      const roomRef   = db.ref('chats/' + roomId);
      const msgsRef   = roomRef.child('messages');
      const presRef   = roomRef.child('presence');
      const readRef   = roomRef.child('readReceipts');

      // Guard: check room + expiry
      roomRef.once('value', snap => {
        if (!snap.exists()) {
          chatEl.innerHTML = '<div class="group"><div class="bubble">This chat has expired or does not exist.</div></div>';
          inputEl.disabled = true; sendBtn.disabled = true;
          return;
        }
        const data = snap.val() || {};
        if (data.expires_at && Date.now() > new Date(data.expires_at).getTime()) {
          chatEl.innerHTML = '<div class="group"><div class="bubble">This chat has expired.</div></div>';
          inputEl.disabled = true; sendBtn.disabled = true;
          return;
        }
      });

      // Presence: I am online
      const myPresenceRef = presRef.child(myId || 'anon');
      function setOnline(state){
        myPresenceRef.update({ online: !!state, lastActive: Date.now(), name: myName }).catch(()=>{});
      }
      setOnline(true);
      window.addEventListener('beforeunload', ()=> setOnline(false));
      document.addEventListener('visibilitychange', ()=> setOnline(document.visibilityState==='visible'));

      // Presence: watch peer
      const peerPresenceRef = presRef.child(peerId || 'peer');
      peerPresenceRef.on('value', s=>{
        const v = s.val() || {};
        if (v.online) {
          statusEl.textContent = 'Online';
        } else if (v.lastActive) {
          const mins = Math.max(1, Math.round((Date.now()-v.lastActive)/60000));
          statusEl.textContent = 'Last seen ' + mins + 'm ago';
        } else {
          statusEl.textContent = 'Offline';
        }
      });

      // Read receipts: when I see messages, update my lastReadAt
      const myReadRef = readRef.child(myId || 'anon');
      function markRead(){
        myReadRef.set(Date.now()).catch(()=>{});
      }
      // mark as read when at bottom or window visible
      chatEl.addEventListener('scroll', ()=> { if(atBottom()) markRead(); });
      document.addEventListener('visibilitychange', ()=> { if(document.visibilityState==='visible') markRead(); });

      // Cache peer's lastReadAt to show "Seen"
      let peerLastReadAt = 0;
      const peerReadRef = readRef.child(peerId || 'peer');
      peerReadRef.on('value', s=>{
        peerLastReadAt = s.val() || 0;
        // re-render tick marks
        document.querySelectorAll('[data-ts]').forEach(el=>{
          const ts = Number(el.dataset.ts||0);
          if (ts && ts <= peerLastReadAt) {
            el.textContent = '✔✔ Seen';
            el.style.opacity = 0.95;
          }
        });
      });

      // Render one message node
      function renderMsg(key, m){
        const isMe = (m.senderId === myId);
        const group = document.createElement('div');
        group.className = 'group ' + (isMe ? 'me' : 'peer');

        // avatar (only for peer side for cleaner look; show for me on small screens if you want)
        if(!isMe){
          const av = document.createElement('div');
          av.className = 'avatar';
          av.textContent = initials(m.senderName || peerName);
          av.style.background = colorFromName(m.senderName || peerName);
          group.appendChild(av);
        }else{
          // keep spacing aligned
          const spacer = document.createElement('div');
          spacer.style.width = '40px';
          spacer.style.height = '1px';
          group.appendChild(spacer);
        }

        const bubble = document.createElement('div');
        bubble.className = 'bubble ' + (isMe ? 'me' : 'peer');

        const text = document.createElement('div');
        text.className = 'msg-text';
        text.textContent = m.text || '';
        bubble.appendChild(text);

        const meta = document.createElement('div');
        meta.className = 'meta';

        const time = document.createElement('span');
        time.className = 'time';
        time.textContent = fmtTime(m.time || Date.now());
        meta.appendChild(time);

        const ticks = document.createElement('span');
        ticks.className = 'ticks';
        ticks.dataset.ts = String(m.time || 0);

        if (isMe){
          // single tick (sent) by default
          if ((m.time || 0) <= peerLastReadAt){
            ticks.textContent = '✔✔ Seen';
          } else {
            ticks.textContent = '✔ Sent';
            ticks.style.opacity = 0.7;
          }
          meta.appendChild(ticks);
        }

        bubble.appendChild(meta);
        group.appendChild(bubble);
        chatEl.appendChild(group);
      }

      // Listen for new messages
      msgsRef.limitToLast(200).on('child_added', snap=>{
        const m = snap.val() || {};
        renderMsg(snap.key, m);
        if (atBottom()) scrollToBottom();
        // If it's a peer message and window is visible, mark read
        if ((m.senderId !== myId) && document.visibilityState==='visible') {
          markRead();
        }
      });

      // Send
      function send(){
        const text = (inputEl.value || '').trim();
        if(!text) return;
        const msgRef = msgsRef.push();
        msgRef.set({
          text,
          time: Date.now(),
          senderId: myId,
          senderName: myName
        }).then(()=>{
          inputEl.value = '';
          scrollToBottom();
        }).catch(()=>{ /* ignore */ });
      }
      sendBtn.addEventListener('click', send);
      inputEl.addEventListener('keydown', (e)=>{
        if(e.key === 'Enter'){ e.preventDefault(); send(); }
      });

      // First render mark read after small delay to ensure UI ready
      setTimeout(()=>{ if(atBottom()) markRead(); }, 400);
    }
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