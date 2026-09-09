// Content mesh: turn wiki-intro mentions of other DB entries into internal links.
export type MeshEntry = { title: string; slug: string; board: string };

export function introHtml(raw: string | undefined, mesh: MeshEntry[], self: string): string {
  if (!raw) return "";
  let t = raw
    .replace(/\{\{[\s\S]*?\}\}/g, " ")
    .replace(/\[\[(?:[^\]|]*\|)?([^\]]*)\]\]/g, "$1")
    .replace(/'''|''/g, "")
    .replace(/<ref[^>]*>[\s\S]*?<\/ref>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\{\||\|\}|\|-/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (t.length < 25) return "";
  const selfKey = self.toLowerCase();
  const others = mesh
    .filter((e) => {
      const k = e.title.toLowerCase();
      return k !== selfKey && e.title.length >= 4 && t.toLowerCase().includes(k);
    })
    .sort((a, b) => b.title.length - a.title.length);
  if (!others.length) return t;
  const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const re = new RegExp("\\b(" + others.map((o) => esc(o.title)).join("|") + ")\\b", "gi");
  const used = new Set<string>();
  let count = 0;
  return t.replace(re, (m) => {
    const key = m.toLowerCase();
    if (used.has(key)) return m;
    const e = others.find((o) => o.title.toLowerCase() === key);
    if (!e) return m;
    used.add(key);
    if (++count > 8) return m;
    return `<a href="/${e.board}/${e.slug}/">${m}</a>`;
  });
}
