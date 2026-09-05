export function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export function inlineMd(text) {
  let t = escapeHtml(text);
  t = t.replace(/`([^`\n]+)`/g, "<code>$1</code>");
  t = t.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  t = t.replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  t = t.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
  t = t.replace(
    /\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
  );
  return t;
}

export function renderMarkdown(text) {
  const blocks = [];
  const t = String(text).replace(/```([\s\S]*?)```/g, (_, code) => {
    blocks.push("<pre><code>" + escapeHtml(code.trim()) + "</code></pre>");
    return "\u0000B" + (blocks.length - 1) + "\u0000";
  });
  const html = [];
  let inList = null;
  let para = null;
  const flushPara = () => {
    if (para != null) {
      html.push("<p>" + para.join("<br>") + "</p>");
      para = null;
    }
  };
  const pushList = (tag) => {
    if (inList !== tag) {
      if (inList) html.push("</" + inList + ">");
      inList = tag;
      html.push("<" + tag + ">");
    }
  };
  for (const raw of t.split("\n")) {
    const line = raw;
    const trim = line.trim();
    const ph = trim.match(/^\u0000B(\d+)\u0000$/);
    if (ph) {
      flushPara();
      if (inList) { html.push("</" + inList + ">"); inList = null; }
      html.push(blocks[Number(ph[1])]);
      continue;
    }
    if (trim === "") {
      flushPara();
      if (inList) { html.push("</" + inList + ">"); inList = null; }
      continue;
    }
    const h = trim.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushPara();
      if (inList) { html.push("</" + inList + ">"); inList = null; }
      const lvl = Math.min(6, h[1].length);
      html.push("<h" + lvl + ">" + inlineMd(h[2]) + "</h" + lvl + ">");
      continue;
    }
    const ul = trim.match(/^[-*]\s+(.*)$/);
    if (ul) { flushPara(); pushList("ul"); html.push("<li>" + inlineMd(ul[1]) + "</li>"); continue; }
    const ol = trim.match(/^\d+[.)]\s+(.*)$/);
    if (ol) { flushPara(); pushList("ol"); html.push("<li>" + inlineMd(ol[1]) + "</li>"); continue; }
    const q = trim.match(/^>\s?(.*)$/);
    if (q) {
      flushPara();
      if (inList) { html.push("</" + inList + ">"); inList = null; }
      html.push("<blockquote>" + inlineMd(q[1]) + "</blockquote>");
      continue;
    }
    if (inList) { html.push("</" + inList + ">"); inList = null; }
    if (para == null) para = [];
    para.push(inlineMd(line));
  }
  flushPara();
  if (inList) html.push("</" + inList + ">");
  return html.join("\n").replace(/\u0000B(\d+)\u0000/g, (_, i) => blocks[Number(i)] || "");
}

export function mdSafe(text) {
  return { __html: renderMarkdown(text) };
}