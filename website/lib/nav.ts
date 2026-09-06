export const NAV = [
  { href: "/", title: "Overview", file: "README.md", group: "Guide" },
  { href: "/diagnostics", title: "Diagnostics", file: "diagnostics.md", group: "Guide" },
  { href: "/cli", title: "CLI", file: "cli.md", group: "Reference" },
  { href: "/adapters", title: "Adapters", file: "adapters.md", group: "Reference" },
  { href: "/datasets", title: "Datasets", file: "datasets.md", group: "Reference" },
  { href: "/python-api", title: "Python API", file: "python-api.md", group: "Reference" },
] as const;

export type NavItem = (typeof NAV)[number];

export function neighbors(href: string): { prev: NavItem | null; next: NavItem | null } {
  const idx = NAV.findIndex((item) => item.href === href);
  return {
    prev: idx > 0 ? NAV[idx - 1] : null,
    next: idx >= 0 && idx < NAV.length - 1 ? NAV[idx + 1] : null,
  };
}
