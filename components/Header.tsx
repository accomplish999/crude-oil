"use client";

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
      <div className="header-inner" style={{ alignItems: "center" }}>
        <a
          className="brand"
          href="https://accompli.sh/"
          aria-label="Home"
          style={{ display: "block", flex: "0 0 auto", lineHeight: 0 }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="https://accompli.sh/brand/pill-flat.png"
            alt=""
            width={2172}
            height={724}
            draggable={false}
            style={{ display: "block", height: "clamp(56px, 7vw, 72px)", width: "auto" }}
          />
        </a>
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
