import type { Metadata } from "next";
import { ChatPanel } from "@/components/ChatPanel";
import { Record } from "@/components/Record";
import { Workbench } from "@/components/Workbench";
import { readCatalog, readChangelog, readMetrics, readStudies, siteUrl } from "@/lib/archive";
import { faq, structuredData } from "@/lib/copy";

const title = "Crude oil prices, stocks, and positions";
const description =
  "EIA WTI and Brent, weekly barrels, the NYMEX contracts EIA posts, and CFTC managed money. Every print keeps its source and retrieval time. Holdout starts 1 Jan 2020.";

export const metadata: Metadata = {
  title: { absolute: title },
  description,
  alternates: { canonical: "/" },
  keywords: ["WTI", "Brent", "Cushing", "CFTC commitments of traders", "crack spread", "EIA weekly petroleum", "contango"],
  openGraph: {
    title,
    description,
    url: "/",
    siteName: "Crude oil",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
  },
};

const pins = ["RWTC", "RBRTE", "CUSHING", "CL1_MINUS_CL4"];

export default function HomePage() {
  const catalog = readCatalog();
  const studies = readStudies();
  const metrics = readMetrics();
  const changelog = readChangelog();
  const questions = faq(catalog);
  const graph = structuredData(catalog, questions, siteUrl);
  const picked = pins
    .map((id) => catalog.series.find((item) => item.id === id))
    .filter((item) => item != null);
  const curve = catalog.series.find((item) => item.id === "RCLC1");
  const spot = catalog.series.find((item) => item.id === "RWTC");

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(graph) }} />
      <header id="overview">
        <p className="kicker">Retrieved {catalog.retrieved_at}</p>
        <h1>The print, with the file still attached.</h1>
        <p className="dek">
          One page for the Cushing spot, Brent, weekly barrels, the four NYMEX months EIA publishes, and CFTC managed money.
          A blank cell stays blank. The date under a figure is the last stored print, not today.
        </p>
      </header>

      <div className="stat-row">
        {picked.map((item) => (
          <a key={item.id} className="stat" href="#sheet">
            <span className="label">{item.id}</span>
            <strong>{item.last_value}</strong>
            <em>
              {item.end}
              <br />
              {item.source} · {item.retrieved_at.slice(0, 10)}
            </em>
          </a>
        ))}
      </div>

      <Workbench
        defaultStart="2020-01-01"
        curveEnd={curve?.end ?? ""}
        spotEnd={spot?.end ?? ""}
      />
      <Record catalog={catalog} studies={studies} metrics={metrics} changelog={changelog} />

      <section id="chat" className="panel">
        <h2>Ask the archive</h2>
        <p className="dek">
          Questions stay on the stored series, the derived metrics, and the studies. The reply has to come back with the rows it used.
          Anything else is refused. With a free Gemini key on the server, the model calls the same tools. With no key, the tools answer locally and the reply says so.
          There is no web search on this route.
        </p>
        <ChatPanel />
      </section>
    </>
  );
}
