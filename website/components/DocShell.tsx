import { extractToc } from "@/lib/docs";
import { neighbors } from "@/lib/nav";
import { Sidebar } from "@/components/Sidebar";

export function DocShell({ href, html }: { href: string; html: string }) {
  const toc = extractToc(html);
  const { prev, next } = neighbors(href);

  return (
    <div className="shell">
      <Sidebar current={href} />
      <div className="stage">
        <main className="doc">
          <div className="prose" dangerouslySetInnerHTML={{ __html: html }} />
          <nav className="pager" aria-label="Page">
            {prev ? (
              <a href={prev.href} className="pager-link prev">
                <span className="pager-dir">Previous</span>
                <span className="pager-title">{prev.title}</span>
              </a>
            ) : (
              <span />
            )}
            {next ? (
              <a href={next.href} className="pager-link next">
                <span className="pager-dir">Next</span>
                <span className="pager-title">{next.title}</span>
              </a>
            ) : null}
          </nav>
        </main>
        {toc.length > 1 ? (
          <aside className="toc" aria-label="On this page">
            <p className="toc-label">On this page</p>
            <ul>
              {toc.map((item) => (
                <li key={item.id}>
                  <a href={`#${item.id}`}>{item.text}</a>
                </li>
              ))}
            </ul>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
