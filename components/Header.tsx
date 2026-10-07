"use client";

import Link from "next/link";

const links = [
  { href: "/#overview", label: "Overview" },
  { href: "/#charts", label: "Chart" },
  { href: "/#sheet", label: "Sheet" },
  { href: "/#metrics", label: "Metrics" },
  { href: "/#risk", label: "Risk" },
  { href: "/#studies", label: "Studies" },
  { href: "/#notes", label: "Notes" },
  { href: "/#chat", label: "Chat" },
  { href: "/#sources", label: "Sources" },
];

export function Header() {
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link className="brand" href="/#overview">
          Crude oil
        </Link>
        <nav className="nav" aria-label="Sections">
          {links.map((link) => (
            <a key={link.href} href={link.href}>
              {link.label}
            </a>
          ))}
        </nav>
      </div>
    </header>
  );
}
