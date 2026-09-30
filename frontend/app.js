const $ = (s) => document.querySelector(s);
const escapeHTML = (s) =>
  String(s).replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let tasks = [],
  progress = {},
  token = "",
  current = null,
  busy = false,
  drafts = {},
  prDraft = { comment: "", tag: "" };
async function api(path, body) {
  const response = await fetch("/api/" + path, {
    method: body === undefined ? "GET" : "POST",
    headers: { "Content-Type": "application/json", "X-GetGood-Token": token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw Error(
      typeof data.detail === "string"
        ? data.detail
        : "Invalid submission. Check the selected line and test code.",
    );
  return data;
}
function notice(text) {
  $("#message").className = text ? "notice" : "";
  $("#message").textContent = text;
}
function navigation(name) {
  for (const id of ["practice", "growth", "pr"])
    $("#nav-" + id).classList.toggle("active", id === name);
  $("#crumb").textContent = {
    practice: "PRACTICE ARENA",
    growth: "GROWTH RECORD",
    pr: "PR GATEKEEPER PREVIEW",
  }[name];
  notice("");
}
function button(id, fn) {
  $("#" + id).onclick = fn;
}
async function guarded(fn) {
  if (busy) return;
  busy = true;
  document.querySelectorAll("button").forEach((b) => (b.disabled = true));
  notice("Running real Python tests…");
  try {
    await fn();
  } catch (e) {
    notice(e.message);
  } finally {
    busy = false;
    document.querySelectorAll("button").forEach((b) => (b.disabled = false));
  }
}
async function overview() {
  navigation("practice");
  progress = await api("progress");
  $("#view").innerHTML =
    `<div class="intro"><div><div class="eyebrow">FROM AI OUTPUT TO YOUR OWN JUDGEMENT</div><h1>Don't just spot the bug.<br>Prove your judgement.</h1><p>Review the code. Build the evidence. Know what you haven't verified. Three exercises, one deliberate learning journey.</p></div><div class="metric"><span class="eyebrow">REPEATED OPERATIONS</span><b>${escapeHTML(progress.level)}</b><small class="muted">${progress.history.length} recorded submissions</small></div></div><div class="cards">${tasks.map((t, i) => `<article class="card"><span class="tag">${t.stage.toUpperCase()}</span><div class="number">0${i + 1}</div><h2>${escapeHTML(t.title)}</h2><p>${["Learn to support a risk judgement with a test. Guidance is available when you need it.", "Transfer your judgement to another business context. No hints this time.", "Recognise a legitimate request. Good judgement also means knowing when to let it through."][i]}</p><button class="primary" data-task="${t.id}">Open exercise <span aria-hidden="true">↗</span></button></article>`).join("")}</div><div class="strip"><div><b>Evidence over confidence.</b><br><small>Your tests run against a reference implementation and hidden faulty variants.</small></div><div><b>No AI scoring</b><br><small>Deterministic rules · Real pytest execution</small></div></div>`;
  document
    .querySelectorAll("[data-task]")
    .forEach((b) => (b.onclick = () => exercise(b.dataset.task)));
}
function payload() {
  return {
    task_id: current.id,
    tests: $("#tests").value,
    judgements: $("#no-risk").checked
      ? []
      : [{ line: Number($("#line").value), type: $("#risk").value }],
    boundaries: Object.fromEntries(
      current.boundaries.map((b) => [b.id, $("#boundary-" + b.id).value]),
    ),
    consequence: $("#consequence").value || null,
  };
}
function fill(data) {
  $("#tests").value = data.tests;
  $("#no-risk").checked = !data.judgements.length;
  $("#line").value = data.judgements[0]?.line || 1;
  $("#risk").value = data.judgements[0]?.type || "duplicate";
  $("#consequence").value = data.consequence || "";
  for (const b of current.boundaries)
    $("#boundary-" + b.id).value = data.boundaries[b.id] || "unverified";
  syncJudgement();
}
function syncJudgement() {
  const disabled = $("#no-risk").checked;
  $("#line").disabled = disabled;
  $("#risk").disabled = disabled;
  const hideConsequence = current.stage !== "Exception" && disabled;
  $(".consequence-field").hidden = hideConsequence;
  $(".evidence-title").textContent =
    `${hideConsequence ? "03" : "04"} / WRITE THE EVIDENCE`;
  $(".boundary-title").textContent =
    `${hideConsequence ? "04" : "05"} / DECLARE YOUR BOUNDARIES`;
  document
    .querySelectorAll(".code-line")
    .forEach((b) =>
      b.classList.toggle(
        "selected",
        !disabled && Number(b.dataset.line) === Number($("#line").value),
      ),
    );
}
function exercise(id) {
  navigation("practice");
  current = tasks.find((t) => t.id === id);
  const t = current;
  $("#view").innerHTML =
    `<button class="back" id="back">← All exercises</button><div class="eyebrow">${t.stage.toUpperCase()} / EXERCISE ${tasks.indexOf(t) + 1}</div><h1>${escapeHTML(t.title)}</h1><div class="toolbar"><span class="demo-label">PRESENTATION SHORTCUTS</span><button class="secondary" id="demo-bad">Load ${t.stage === "Exception" ? "overblocking" : "first attempt"} example</button><button class="secondary" id="demo-good">Load evidence example</button><span class="demo-label">Examples fill the form; Submit still runs tests.</span></div><div class="split"><div><section class="panel"><div class="panel-title">01 / UNDERSTAND THE REQUIREMENT</div><p>${escapeHTML(t.description)}</p><small class="muted">Scope: sequential operations, integer cents. Concurrency is not verified.</small></section><section class="panel"><div class="panel-title">CODE UNDER REVIEW · CLICK A LINE TO MARK IT</div><div class="code">${t.code
      .trimEnd()
      .split("\n")
      .map(
        (l, i) =>
          `<button class="code-line" data-line="${i + 1}"><span class="ln">${i + 1}</span>${escapeHTML(l)}</button>`,
      )
      .join(
        "",
      )}</div></section><section class="panel"><h3>Test toolkit</h3><p class="muted">Use <code>env.make_payment(amount_cents=10_000)</code> or <code>env.make_campaign(remaining=5)</code>. Call the code through <code>env.svc</code>.</p><p class="muted">Inspect <code>env.gateway.calls</code>, <code>env.wallet.calls</code> and <code>env.db</code>. Each test starts with fresh state.</p>${t.stage === "Guided" ? '<button id="hint" class="secondary">Get the next hint</button><div id="hint-text"></div>' : '<span class="tag">NO HINTS IN THIS STAGE</span>'}</section></div><div><section class="panel"><div class="panel-title">02 / MAKE A JUDGEMENT</div><label><input type="checkbox" id="no-risk" checked>No risk found within the stated scope</label><div class="row"><div class="field"><label for="line">Code line</label><input id="line" type="number" min="1" max="${t.code.trimEnd().split("\n").length}" value="1"></div><div class="field"><label for="risk">Risk type</label><select id="risk"><option value="duplicate">Repeated operation</option><option value="precision">Amount precision</option><option value="over_limit">Over limit</option><option value="concurrent">Concurrency</option><option value="state">Invalid state</option><option value="other">Other</option></select></div></div><div class="consequence-field"><div class="panel-title">03 / EXPLAIN THE CONSEQUENCE</div><label for="consequence">${t.stage === "Exception" ? "What should happen to a second refund with a new request_id?" : "What can happen when the same request_id is retried?"}</label><select id="consequence"><option value="">Choose an outcome…</option><option value="duplicate_effect">The external refund or voucher is issued twice</option><option value="legitimate_request">A new request is allowed as a separate operation</option><option value="unrelated">Only the screen label changes</option></select></div><div class="panel-title section-gap evidence-title">04 / WRITE THE EVIDENCE</div><label for="tests">Python tests · pytest</label><textarea id="tests" spellcheck="false" aria-label="Python test editor"></textarea><div class="row"><button id="run" class="secondary">Run on reference</button><small class="muted">A self-check; progress is unchanged.</small></div><div id="run-result" role="status"></div></section><section class="panel"><div class="panel-title boundary-title">05 / DECLARE YOUR BOUNDARIES</div>${t.boundaries.map((b) => `<div class="boundary"><label for="boundary-${b.id}">${escapeHTML(b.label)}</label><select id="boundary-${b.id}"><option value="unverified">Not verified</option><option value="verified">Verified</option><option value="need_mentor">Need guidance</option></select></div>`).join("")}<p class="muted">An honest “not verified” is welcome. A verified claim needs evidence.</p><div class="row"><button id="submit" class="primary">Submit & record →</button><button id="compare" class="secondary">Compare without recording</button></div><p class="muted">Comparison runs the full evaluation. It does not change your growth record or level.</p></section></div></div>`;
  fill(drafts[id] || { tests: t.template, judgements: [], boundaries: {} });
  button("back", () => {
    drafts[id] = payload();
    overview();
  });
  $("#no-risk").onchange = syncJudgement;
  $("#line").oninput = syncJudgement;
  document.querySelectorAll("[data-line]").forEach(
    (b) =>
      (b.onclick = () => {
        $("#no-risk").checked = false;
        $("#line").value = b.dataset.line;
        syncJudgement();
      }),
  );
  $("#tests").onkeydown = (e) => {
    if (e.key === "Tab") {
      e.preventDefault();
      const el = e.target;
      const start = el.selectionStart,
        end = el.selectionEnd;
      el.setRangeText("    ", start, end, "end");
    }
  };
  for (const kind of ["good", "bad"])
    button("demo-" + kind, async () => {
      try {
        fill(await api(`demo/${id}/${kind}`));
        notice(
          "Presentation example loaded. Click Submit to run the real tests.",
        );
      } catch (e) {
        notice(e.message);
      }
    });
  if (t.stage === "Guided")
    button("hint", async () => {
      const h = await api("hint/" + id, {});
      $("#hint-text").className = "hint";
      $("#hint-text").textContent = `Hint ${h.used}/3: ${h.text}`;
    });
  button("run", () =>
    guarded(async () => {
      const r = await api("run", payload());
      $("#run-result").className = "hint";
      $("#run-result").textContent =
        `Reference: ${r.status} · ${r.tests} tests. ${r.details.join(", ")}`;
      notice("Reference self-check complete.");
    }),
  );
  button("compare", () =>
    guarded(async () => {
      drafts[id] = payload();
      feedback(await api("compare", drafts[id]));
    }),
  );
  button("submit", () =>
    guarded(async () => {
      drafts[id] = payload();
      const result = await api("submit", drafts[id]);
      feedback(result);
    }),
  );
}
const variantCoaching = {
  t1_refund: {
    v1: "Call refund twice with the same request_id. Without deduplication, the gateway receives two refunds.",
    v2: "Call refund twice with the same request_id. Checking the key after gateway.refund still sends two gateway calls.",
    v3: "Use two distinct request IDs for the same amount. Both refunds are valid; a key based on amount blocks the second.",
  },
  t2_coupon: {
    v1: "Claim twice with the same request_id. Without deduplication, the wallet receives two vouchers.",
    v2: "Claim twice with the same request_id. Checking after wallet.add still grants two vouchers.",
    v3: "Claim twice with different request IDs. Both claims are valid while stock remains; a user-based key blocks the second.",
  },
  t3_legit_refund: {
    v1: "Retry the same request_id. Without deduplication, the gateway is called twice.",
    v2: "Retry the same request_id. Checking after the gateway call still repeats the external refund.",
    v3: "Refund the same amount under r-1 and r-2. The second request is legitimate; amount-based deduplication blocks it.",
  },
};
const row = (a, b, good) =>
  `<div class="result-row"><span>${escapeHTML(a)}</span><span class="${good ? "pass" : "fail"}">${escapeHTML(b)}</span></div>`;
function feedback(r) {
  notice("");
  const t = current;
  const ref = r.reference.status;
  const hideDetails = t.stage === "Guided" && r.judgement.missed.length > 0;
  $("#view").innerHTML =
    `${r.recorded === false ? '<div class="hint">COMPARISON ONLY · Not recorded · Level unchanged</div>' : ""}<div class="eyebrow">EVIDENCE REPORT / ${escapeHTML(t.title.toUpperCase())}</div><h1>${r.success ? "Your judgement has evidence." : "A chance to sharpen your judgement."}</h1><p class="muted">${escapeHTML(r.reason)} No AI score, and no cached result.</p><div class="result-grid"><section class="panel"><div class="panel-title">01 / JUDGEMENT</div>${row("Decision", r.judgement.correct ? "Correct" : "Needs revision", r.judgement.correct)}${row("Risks missed", r.judgement.missed.length, !r.judgement.missed.length)}${row("False positives", r.judgement.false_positive.length, !r.judgement.false_positive.length)}${hideDetails ? "" : row("Consequence judgement", r.consequence?.correct ? "Correct" : "Needs revision", r.consequence?.correct)}${t.stage === "Guided" && r.judgement.missed.length ? '<p class="muted">There is still a risk to find. Return to the exercise and try a hint.</p>' : ""}</section><section class="panel"><div class="panel-title">02 / TEST EVIDENCE</div>${row("Reference implementation", ref, ref === "passed")}${ref === "failed" ? '<p class="fail">Your assertions reject correct behaviour. Check for overblocking or an incorrect test expectation.</p>' : ""}${["error", "timeout"].includes(ref) ? '<p class="fail">Execution problem. This is not evidence of a detected risk.</p>' : ""}${Object.entries(
      r.variants,
    )
      .map(
        ([v, result]) =>
          row(
            hideDetails
              ? "Hidden variant " + v.toUpperCase()
              : variantDescriptions[v],
            result.caught
              ? "Caught"
              : result.status === "passed"
                ? "Not caught"
                : result.status,
            result.caught,
          ) +
          (hideDetails
            ? ""
            : `<p class="coaching">${escapeHTML(variantCoaching[t.id][v])}</p>`),
      )
      .join(
        "",
      )}<small class="muted">Failed tests: ${escapeHTML(r.reference.details.join(", ") || "None on reference")}</small></section><section class="panel"><div class="panel-title">03 / BOUNDARIES</div>${t.boundaries.map((b) => row(b.label, r.boundaries[b.id].replaceAll("_", " "), r.boundaries[b.id] !== "unsupported")).join("")}</section><section class="panel"><div class="panel-title">04 / GROWTH RECORD</div><h2>${escapeHTML(r.previous_level || r.level)} → ${escapeHTML(r.level)}</h2><p>${escapeHTML(r.level_reason || r.reason)}</p><p class="muted">Hints used: ${r.hints_used}. Concurrent operations: ${escapeHTML(concurrencyLabel(r.boundaries.concurrent))}.</p><small class="muted">This is task evidence, not a general certification of competence.</small></section></div><div class="row"><button class="secondary" id="retry">← Revise this submission</button><button class="primary" id="next">${tasks.indexOf(t) < 2 ? "Next exercise →" : "View growth record →"}</button></div>`;
  button("retry", () => exercise(t.id));
  button("next", () =>
    tasks.indexOf(t) < 2 ? exercise(tasks[tasks.indexOf(t) + 1].id) : growth(),
  );
}
const variantDescriptions = {
  v1: "Retry executes the operation twice",
  v2: "External side effect happens before deduplication",
  v3: "Legitimate new request is blocked",
};
function concurrencyLabel(status) {
  return status === "need_mentor"
    ? "Needs guidance"
    : status === "unsupported"
      ? "Needs guidance — verified claim unsupported"
      : "Not verified";
}
function evidenceDetails(h) {
  const r = h.result,
    t = tasks.find((t) => t.id === h.task_id);
  const hidden = t?.stage === "Guided" && r.judgement.missed.length > 0;
  return `<details class="case-evidence"><summary>Inspect case evidence</summary>
 ${row("Risks missed", r.judgement.missed.length, !r.judgement.missed.length)}
 ${row("Risk judgements falsely flagged", r.judgement.false_positive.length, !r.judgement.false_positive.length)}
 ${hidden ? "" : row("Consequence judgement", r.consequence?.correct ? "Correct" : "Needs revision", r.consequence?.correct)}
 ${row("Legitimate reference behaviour", r.reference.status === "passed" ? "Accepted by tests" : r.reference.status === "failed" ? "Rejected by tests" : r.reference.status, r.reference.status === "passed")}
 <p class="muted">A rejected reference may indicate overblocking or an incorrect test expectation.</p>
 ${Object.entries(r.variants)
   .map(
     ([v, result]) =>
       row(
         hidden ? "Hidden variant " + v.toUpperCase() : variantDescriptions[v],
         result.caught
           ? "Caught"
           : result.status === "passed"
             ? "Not caught"
             : result.status,
         result.caught,
       ) +
       (hidden
         ? ""
         : `<p class="coaching">${escapeHTML(variantCoaching[h.task_id][v])}</p>`),
   )
   .join("")}
 <h3>Boundary declarations and evidence</h3>
 ${(t?.boundaries || []).map((b) => row(b.label, (h.boundary_claims?.[b.id] || { supported: "verified", unsupported: "verified" }[r.boundaries[b.id]] || r.boundaries[b.id]).replaceAll("_", " ") + " → " + r.boundaries[b.id].replaceAll("_", " "), r.boundaries[b.id] === "supported")).join("")}
 <p>${escapeHTML(h.reason || "")}</p><p class="muted">${escapeHTML(h.level_reason || "Level explanation was not recorded for this earlier submission.")}</p></details>`;
}
async function growth() {
  navigation("growth");
  progress = await api("progress");
  const latest = [...progress.history]
    .reverse()
    .find((h) => h.result?.boundaries?.concurrent);
  $("#view").innerHTML =
    `<div class="eyebrow">THE RECORD BEHIND THE LABEL</div><h1>Growth you can inspect.</h1><p class="muted">Every level is backed by exercise results, hint use and declared boundaries.</p>
 <div class="strip"><div><span class="eyebrow">REPEATED OPERATIONS</span><h2>${escapeHTML(progress.level)}</h2></div><div><span class="eyebrow">CONCURRENT OPERATIONS</span><h2>${escapeHTML(concurrencyLabel(latest?.result.boundaries.concurrent))}</h2><small>Based on the latest recorded declaration. Concurrency has no validator.</small></div></div>
 <section class="panel" style="margin-top:24px"><h3>Submission history</h3>${progress.history.length ? progress.history.map((h, i) => `<article class="history-case"><h3>${i + 1}. ${escapeHTML(h.title)}</h3><p>${escapeHTML(h.previous_level || (i ? progress.history[i - 1].level : "Needs guidance"))} → <b>${escapeHTML(h.level)}</b></p><p class="${h.result.success ? "pass" : "fail"}">${h.result.success ? "Evidence accepted" : "Needs revision"} · ${h.hints_used} hints</p>${evidenceDetails(h)}</article>`).join("") : '<div class="empty">No submissions yet. Start in the practice room.</div>'}</section>
 <p class="muted">Verified across scenarios requires independent success in the coupon and refund-exception exercises. An unsuccessful recorded submission lowers the level by one. Comparisons never affect this record.</p>`;
}
function practiceSequence(record) {
  return tasks
    .map((task, index) => {
      const accepted = record.history.some(
        (entry) => entry.task_id === task.id && entry.result.success,
      );
      const attempted = record.history.some(
        (entry) => entry.task_id === task.id,
      );
      const status = accepted
        ? "Evidence accepted"
        : attempted
          ? "Needs revision"
          : "Not started";
      return `<li class="sequence-step"><div><b>${index + 1}. ${escapeHTML(task.title)}</b><br><small>${escapeHTML(status)} · ${escapeHTML(task.stage)}</small></div><button class="secondary" data-pr-task="${task.id}">Open exercise →</button></li>`;
    })
    .join("");
}
async function pr() {
  navigation("pr");
  const record = await api("progress");
  $("#view").innerHTML =
    `<div class="wide"><span class="tag">CONCEPT PREVIEW · ONE PREPARED PR · NOT CONNECTED TO GITHUB</span><h1>Turn a review gap<br>into the next exercise.</h1>
 <section class="panel"><div class="panel-title">PULL REQUEST #42 / ADD PARTIAL REFUNDS</div><h3>01 / Junior self-review</h3><p>Checked the refund limit and resulting balance. No repeated-operation risk flagged.</p><div class="log"><b>Submitted evidence</b><p>A single refund updates the balance correctly.</p><b>Learner boundary</b><p>Sequential retries and concurrent arrivals are not verified.</p></div></section>
 <section class="panel"><h3>02 / Senior review</h3><p>A retry reached the payment gateway twice. Add a review comment and confirm the risk tag for this prepared case.</p><label for="senior-comment">Senior review comment</label><textarea id="senior-comment" class="short-editor" placeholder="What did the junior miss?">${escapeHTML(prDraft.comment)}</textarea><label><input type="radio" name="senior-risk" value="duplicate" ${prDraft.tag === "duplicate" ? "checked" : ""}> Duplicate request</label><button class="secondary" id="confirm-tag">Compare with junior self-review →</button></section>
 <section class="panel" id="practice-match"><h3>03 / Targeted practice</h3><p class="muted">Confirm the senior's comment and tag to show the review gap and mapped practice sequence.</p></section>
 <p class="muted">This is a prepared PR example. The comment and tag are local to this page; no GitHub comment is posted. Senior review remains the safety net.</p></div>`;
  $("#senior-comment").oninput = (e) => {
    prDraft.comment = e.target.value;
  };
  document.querySelectorAll('[name="senior-risk"]').forEach(
    (input) =>
      (input.onchange = (e) => {
        prDraft.tag = e.target.value;
      }),
  );
  button("confirm-tag", () => {
    if (!prDraft.comment.trim() || prDraft.tag !== "duplicate") {
      notice("Enter the senior comment and select the confirmed risk tag.");
      return;
    }
    notice("Senior tag compared with this prepared junior self-review.");
    $("#practice-match").innerHTML =
      `<h3>03 / A missed risk becomes targeted practice</h3>
   ${row("Junior self-review", "Duplicate request not flagged", false)}${row("Senior-confirmed tag", "Duplicate request", true)}
   <p><b>Senior comment:</b> ${escapeHTML(prDraft.comment.trim())}</p><p><b>Review gap:</b> repeated external operations were not tested.</p>
   <ol class="sequence">${practiceSequence(record)}</ol>
   <p class="muted">Each step shows its recorded local progress. The learner returns to work with tests and an explicit boundary; the senior still reviews the change.</p>`;
    document
      .querySelectorAll("[data-pr-task]")
      .forEach(
        (button) => (button.onclick = () => exercise(button.dataset.prTask)),
      );
  });
}
button("nav-practice", overview);
button("nav-growth", growth);
button("nav-pr", () => pr().catch((e) => notice(e.message)));
$("#home").onclick = (e) => {
  e.preventDefault();
  overview();
};
button("reset", async () => {
  if (confirm("Clear this local learner’s submissions and hints?")) {
    await api("reset", {});
    drafts = {};
    await overview();
  }
});
(async () => {
  try {
    token = (await api("session")).token;
    tasks = await api("tasks");
    await overview();
  } catch (e) {
    notice(
      "Unable to load the demo. Start python run.py and refresh. " + e.message,
    );
  }
})();
