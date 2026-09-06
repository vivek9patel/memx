"use client";

import { useEffect, useState } from "react";
import { NAV } from "@/lib/nav";

const GROUPS = ["Guide", "Reference"] as const;

export function Sidebar({ current }: { current: string }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setOpen(false);
  }, [current]);

  useEffect(() => {
    document.body.classList.toggle("nav-open", open);
    return () => document.body.classList.remove("nav-open");
  }, [open]);

  return (
    <>
      <header className="topbar">
        <button
          type="button"
          className="menu-btn"
          aria-expanded={open}
          aria-controls="docs-nav"
          onClick={() => setOpen((v) => !v)}
        >
          <span className="menu-btn-bars" aria-hidden />
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
        </button>
        <a href="/" className="brand">
          memx
        </a>
      </header>
      {open ? (
        <button
          type="button"
          className="nav-backdrop"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <aside className={`side${open ? " open" : ""}`} id="docs-nav">
        <a href="/" className="brand side-brand">
          memx
        </a>
        <p className="tag">Eval + diagnostics</p>
        <nav>
          {GROUPS.map((group) => (
            <div key={group} className="nav-group">
              <p className="nav-label">{group}</p>
              {NAV.filter((item) => item.group === group).map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className={current === item.href ? "active" : undefined}
                >
                  {item.title}
                </a>
              ))}
            </div>
          ))}
        </nav>
      </aside>
    </>
  );
}
