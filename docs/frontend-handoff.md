# Frontend Integration Handoff — Petition API

This document is for the front-end team wiring `index.html` to the new backend
API (`backend/`, Django + DRF). The backend is merged to `main` and does **not**
touch `index.html` — that's yours. Below is exactly what to change and why.

Full API reference lives in `backend/README.md`. This file focuses on the
concrete edits to `index.html`.

---

## 1. What the backend gives you

Base URL (dev): `http://127.0.0.1:8000/api`

| Method | Path | Request / Response |
|---|---|---|
| `POST` | `/api/signatures/` | Body `{name, email, newsletter, anonymous, consent, message?: {recipient, text}}` → `201 {"status":"ok"}`. On invalid input → `400 {field: ["error", ...]}`. |
| `GET` | `/api/signatures/count/` | `{"count": 1234}` |
| `GET` | `/api/signatures/` | Public signer names, paginated: `{"count": N, "next": url|null, "previous": url|null, "results": [{"name": "...", "created_at": "2026-07-24T09:12:00Z"}]}` |
| `GET` | `/api/messages/` | Published messages, paginated (same envelope): `results: [{"recipient": "...", "text": "...", "created_at": "..."}]` |

Behavior you can rely on:

- **Silent dedupe.** Submitting an email that already signed returns the same
  `201 {"status":"ok"}` — no error, no duplicate. Just show the thank-you state
  regardless.
- **Anonymous.** If `anonymous: true`, the signer still counts but their name is
  never returned by `GET /api/signatures/`.
- **Moderation.** Messages (and names) are public immediately unless the backend
  auto-holds them; held items simply won't appear in the GET endpoints. Nothing
  for the frontend to do.
- **Pagination.** Lists return newest-first, 50 per page. For the comments
  section, page 1 (the 50 most recent) is all you need. `next` is a full URL if
  you ever want to page further.
- **Timestamps** are ISO 8601 strings (`created_at`), not epoch milliseconds —
  parse with `new Date(created_at)`.

---

## 2. Configuration to add

At the top of the IIFE in `index.html`, add a single base-URL constant and drop
the demo seeds:

```js
// --- API ---
var API = "http://127.0.0.1:8000/api"; // TODO: set to production API origin on deploy
```

Remove `SEED_COUNT` and the whole `localStorage` demo layer (`loadSignatureCount`,
`saveSignature`, `loadComments`, `saveComment` bodies) — they're replaced below.
Keep `GOAL = 3000`.

---

## 3. Replace the counter

**Current** (`renderCounter` reads `loadSignatureCount()` from localStorage).
**New** — fetch the real total:

```js
function renderCounter(count){
  var pct = Math.min(100, (count / GOAL) * 100);
  document.getElementById('signatureCount').textContent = count.toLocaleString('sl-SI');
  document.getElementById('progressFill').style.width = pct + '%';
}

function loadCounter(){
  fetch(API + '/signatures/count/')
    .then(function(r){ return r.json(); })
    .then(function(data){ renderCounter(data.count); })
    .catch(function(){ /* leave counter at 0 on network error */ });
}

loadCounter(); // replaces the old renderCounter() call on page load
```

---

## 4. Replace the form submit

Keep all the existing client-side validation (name/email/consent/recipient
checks) exactly as-is — it's good UX. Only the part after validation changes:
instead of `saveSignature()` / `saveComment()` to localStorage, POST to the API.

Replace the block from `// TODO: send { name, email, ... }` through the success
handling with:

```js
var payload = {
  name: name,
  email: email,
  newsletter: document.getElementById('consentNewsletter').checked,
  anonymous: anonymous, // already read from #signAnonymous above
  consent: consent      // already read from #consentRequired above
};
if (text) {
  payload.message = { recipient: recipient, text: text };
}

var submitBtn = document.getElementById('signBtn');
submitBtn.disabled = true;

fetch(API + '/signatures/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
})
  .then(function(r){
    if (r.status === 201) return r.json();
    if (r.status === 400) {
      return r.json().then(function(errors){ throw errors; }); // field errors
    }
    if (r.status === 429) { throw { _rate: true }; } // throttled (too many submits)
    throw { _network: true };
  })
  .then(function(){
    // Success — signature stored (or silently deduped). Lock the form.
    signForm.querySelectorAll('input, select, textarea, button')
      .forEach(function(el){ el.disabled = true; });
    document.getElementById('signSuccess').style.display = 'block';
    loadCounter();   // refresh the total
    loadComments();  // show the new message (if it was published immediately)
  })
  .catch(function(err){
    submitBtn.disabled = false; // let them retry
    errorBox.style.display = 'block';
    if (err && err._rate) {
      errorBox.textContent = 'Preveč poskusov. Poskusi znova čez nekaj minut.';
    } else if (err && err._network) {
      errorBox.textContent = 'Napaka pri povezavi. Poskusi znova.';
    } else {
      // Field errors from the API (consent/email/name/message).
      errorBox.textContent = 'Prosimo, preveri vnesene podatke in poskusi znova.';
    }
  });
```

Notes:
- `name`, `email`, `consent`, `anonymous`, `recipient`, `text`, `errorBox`, and
  `signForm` are all already defined in the current submit handler — reuse them.
- The API is the source of truth for validation, but keep the existing
  client-side checks so users get instant feedback before a round-trip.

---

## 5. Replace the comments / messages

**Current** `renderComments()` reads localStorage and renders `c.recipient`,
`c.text`, `new Date(c.time)`. Switch it to fetch from the API. The only field
change is `c.time` (epoch) → `c.created_at` (ISO string).

```js
function loadComments(){
  fetch(API + '/messages/')
    .then(function(r){ return r.json(); })
    .then(function(data){ renderComments(data.results); })
    .catch(function(){ renderComments([]); });
}

function renderComments(comments){
  var list = document.getElementById('commentsList');
  list.innerHTML = '';

  if (!comments || comments.length === 0){
    var empty = document.createElement('p');
    empty.className = 'comments-empty';
    empty.textContent = 'Bodi prvi_a, ki napiše sporočilo.';
    list.appendChild(empty);
    return;
  }

  comments.forEach(function(c){
    var item = document.createElement('div');
    item.className = 'comment';

    var meta = document.createElement('div');
    meta.className = 'comment-meta';

    var badge = document.createElement('span');
    badge.className = 'comment-badge';
    badge.textContent = c.recipient;           // textContent — never innerHTML
    meta.appendChild(badge);

    var time = document.createElement('span');
    time.className = 'comment-time';
    time.textContent = new Date(c.created_at)   // <-- was c.time
      .toLocaleString('sl-SI', { dateStyle: 'medium', timeStyle: 'short' });
    meta.appendChild(time);

    item.appendChild(meta);

    var textEl = document.createElement('p');
    textEl.className = 'comment-text';
    textEl.textContent = c.text;                // textContent — user-submitted
    item.appendChild(textEl);

    list.appendChild(item);
  });
}

loadComments(); // replaces the old renderComments() call on page load
```

**Keep using `textContent`** (never `innerHTML`) for `recipient` and `text` —
they're user-submitted. The backend stores them raw; escaping is the frontend's
job at render time, exactly as the current code already does.

---

## 6. Optional: a public "wall of names"

The design includes `GET /api/signatures/` (names of non-anonymous signers) in
case you want a names section. It's not in the current page. If you add one:

```js
fetch(API + '/signatures/')
  .then(function(r){ return r.json(); })
  .then(function(data){
    data.results.forEach(function(sig){
      // sig.name, sig.created_at — render with textContent
    });
  });
```

Anonymous signers and any held names are already excluded server-side.

---

## 7. Running the backend locally (for dev/testing)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
cp .env.example .env
.venv/bin/python manage.py migrate
.venv/bin/python manage.py createsuperuser   # for the /admin/ moderation UI
.venv/bin/python manage.py runserver          # serves API at http://127.0.0.1:8000
```

### CORS — the one gotcha

The API only accepts browser requests from origins listed in
`CORS_ALLOWED_ORIGINS` (in `backend/.env`). The defaults already include
`http://localhost:5500` and `http://127.0.0.1:5500` (VS Code Live Server). If
you serve `index.html` from a different port, add that origin to
`CORS_ALLOWED_ORIGINS` (comma-separated) or your `fetch()` calls will fail with a
CORS error in the console.

On production: set `API` (section 2) to the deployed API origin, and add the
site's real origin to `CORS_ALLOWED_ORIGINS` on the server.

---

## 8. Checklist

- [ ] Add `API` base-URL constant; remove `SEED_COUNT` and localStorage helpers.
- [ ] Counter fetches `/signatures/count/` on load.
- [ ] Submit POSTs to `/signatures/` (message nested only when text present);
      handles 201 / 400 / 429 / network.
- [ ] Comments fetch `/messages/`; render `created_at` (not `time`); keep
      `textContent`.
- [ ] Refresh counter + comments after a successful submit.
- [ ] (Optional) names wall via `/signatures/`.
- [ ] Point `API` at production and configure server CORS before launch.

Questions on API behavior → see `backend/README.md` or ping the backend side.
