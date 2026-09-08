import items from "../data/factorio_items.json";

export function GET() {
  const entries = items
    .map((x) => ({
      title: x.title,
      href: `/items/${x.slug}/`,
      sub: `Item · ${x.time ? x.time + "s craft" : "no recipe"}${x.stack_size ? ` · stack ${x.stack_size}` : ""}`,
      icon: x.icon_file || "",
    }))
    .sort((a, b) => a.title.localeCompare(b.title));
  return new Response(JSON.stringify(entries), {
    headers: { "Content-Type": "application/json; charset=utf-8" },
  });
}
