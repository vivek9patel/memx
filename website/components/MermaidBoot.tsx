"use client";

import { useEffect } from "react";

export function MermaidBoot() {
  useEffect(() => {
    const nodes = document.querySelectorAll(".mermaid");
    if (!nodes.length) return;
    let cancelled = false;
    void import("mermaid").then((mod) => {
      if (cancelled) return;
      const mermaid = mod.default;
      const dark = window.matchMedia("(prefers-color-scheme: dark)").matches;
      mermaid.initialize({
        startOnLoad: false,
        theme: dark ? "dark" : "neutral",
        securityLevel: "strict",
        fontFamily: "inherit",
      });
      void mermaid.run({ querySelector: ".mermaid" });
    });
    return () => {
      cancelled = true;
    };
  }, []);
  return null;
}
