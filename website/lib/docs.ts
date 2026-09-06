import fs from "fs";
import path from "path";
import { remark } from "remark";
import remarkGfm from "remark-gfm";
import remarkHtml from "remark-html";

export type { NavItem } from "@/lib/nav";
export { NAV, neighbors } from "@/lib/nav";

export type TocItem = { id: string; text: string };

function docsDir(): string {
  const candidates = [
    path.join(process.cwd(), "..", "docs"),
    path.join(process.cwd(), "docs"),
    path.resolve(__dirname, "..", "..", "docs"),
    path.resolve(__dirname, "..", "..", "..", "docs"),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(path.join(dir, "README.md"))) return dir;
  }
  throw new Error(
    `memx docs/ not found (cwd=${process.cwd()}). Run npm from website/ with ../docs present.`,
  );
}

function shotsDir(): string {
  const candidates = [
    path.join(process.cwd(), "public", "shots"),
    path.join(process.cwd(), "website", "public", "shots"),
  ];
  for (const dir of candidates) {
    if (fs.existsSync(dir)) return dir;
  }
  return path.join(process.cwd(), "public", "shots");
}

export function readDoc(file: string): string {
  const raw = fs.readFileSync(path.join(docsDir(), file), "utf8");
  return raw
    .replace(/\]\(([a-z0-9-]+)\.md\)/gi, (_m, slug: string) =>
      slug.toLowerCase() === "readme" ? "](/)" : `](/${slug})`,
    )
    .replace(/\]\(\.\.\/website\/public\/shots\//g, "](/shots/")
    .replace(/\]\(website\/public\/shots\//g, "](/shots/");
}

function slugify(htmlInner: string): string {
  const text = htmlInner.replace(/<[^>]+>/g, "").trim();
  return text
    .toLowerCase()
    .replace(/[`*_]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function stripTags(html: string): string {
  return html.replace(/<[^>]+>/g, "").trim();
}

export function decorateHtml(html: string): string {
  const dir = shotsDir();
  let out = html.replace(/<h([23])>([\s\S]*?)<\/h\1>/gi, (_m, level: string, inner: string) => {
    const id = slugify(inner);
    return `<h${level} id="${id}">${inner}</h${level}>`;
  });

  out = out.replace(/<table>/gi, '<div class="table-wrap"><table>').replace(
    /<\/table>/gi,
    "</table></div>",
  );
  out = out.replace(
    /<p>\s*<img src="(\/shots\/[^"]+)" alt="([^"]*)">\s*<\/p>/gi,
    (_m, src: string, alt: string) => figureForShot(dir, src, alt),
  );
  out = out.replace(
    /<img src="(\/shots\/[^"]+)" alt="([^"]*)">/gi,
    (_m, src: string, alt: string) => figureForShot(dir, src, alt),
  );
  return out;
}

function figureForShot(dir: string, src: string, alt: string): string {
  const file = src.replace(/^\/shots\//, "");
  const exists = fs.existsSync(path.join(dir, file));
  if (exists) {
    return `<figure class="shot"><img src="${src}" alt="${alt}" /><figcaption>${alt}</figcaption></figure>`;
  }
  return `<figure class="shot shot-missing"><div class="shot-slot" role="img" aria-label="${alt}"></div><figcaption>${alt} <span class="shot-pending">screenshot pending</span></figcaption></figure>`;
}

export function extractToc(html: string): TocItem[] {
  const items: TocItem[] = [];
  const re = /<h2 id="([^"]+)">([\s\S]*?)<\/h2>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(html)) !== null) {
    items.push({ id: m[1], text: stripTags(m[2]) });
  }
  return items;
}

export async function renderDoc(file: string): Promise<string> {
  const result = await remark().use(remarkGfm).use(remarkHtml).process(readDoc(file));
  return decorateHtml(String(result));
}
