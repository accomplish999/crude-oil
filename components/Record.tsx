import Link from "next/link";
import { StudyChart } from "@/components/StudyChart";
import { explainers, faq } from "@/lib/copy";
import type { Catalog, ChangelogEntry, MetricFile, StudyFile } from "@/lib/types";

const downloads = [
  ["prices.csv", "Prices, CSV"],
  ["prices.parquet", "Prices, Parquet"],
  ["weekly.csv", "Weekly, CSV"],
  ["weekly.parquet", "Weekly, Parquet"],
  ["positions.csv", "Positions, CSV"],
  ["positions.parquet", "Positions, Parquet"],
  ["catalog.csv", "Catalog, CSV"],
];

const linked = [
  ["OPEC Monthly Oil Market Report", "https://www.opec.org/", "OPEC holds the copyright. The tables are not copied."],
  ["IEA oil pages", "https://www.iea.org/energy-system/fossil-fuels/oil", "IEA holds the copyright. Same treatment."],
  ["Baker Hughes rig count", "https://rigcount.bakerhughes.com/", "The workbook is published for readers of that site. It is not mirrored here."],
  ["EIA futures prices", "https://www.eia.gov/dnav/pet/pet_pri_fut_s1_d.htm", "Contracts 1 to 4 are stored. A longer board is an exchange quote."],
  ["CFTC disaggregated file", "https://www.cftc.gov/dea/newcot/c_disagg.txt", "067651 and 06765T are stored. The TFF report does not carry CL."],
];

export function Record({
  catalog,
  studies,
  metrics,
  changelog,
}: {
  catalog: Catalog;
  studies: StudyFile;
  metrics: MetricFile;
  changelog: { entries: ChangelogEntry[] };
}) {
  const notes = explainers(catalog);
  const questions = faq(catalog);
  const latest = changelog.entries[changelog.entries.length - 1];
  const held = metrics.metrics.filter((item) => item.verdict === "held");
  const failed = metrics.metrics.filter((item) => item.verdict === "failed");

  return (
    <>
      <section id="metrics">
        <h2>Derived metrics</h2>
        <p className="dek">
          Each column is arithmetic on stored prints. The formula is on the row. Held means the precommitted bar was met. It is not a trade.
          Failed means the bar was missed. {held.length} met the bar. {failed.length} missed it.
          {metrics.note ? ` ${metrics.note}` : ""}
        </p>
        <div className="table-wrap">
          <table>
            <caption>Metrics scored on the holdout that starts {metrics.holdout_start}</caption>
            <thead>
              <tr>
                <th>Id</th>
                <th>Last</th>
                <th>Verdict</th>
                <th>Formula and result</th>
              </tr>
            </thead>
            <tbody>
              {metrics.metrics.map((item) => (
                <tr key={item.id} id={`metric-${item.id.toLowerCase()}`}>
                  <td>
                    <a href={`#study-${item.study_slug}`}>{item.id}</a>
                  </td>
                  <td>
                    {item.latest_value}
                    {item.latest_date ? <><br />{item.latest_date}</> : null}
                  </td>
                  <td>
                    <span className={`verdict ${item.verdict}`}>{item.verdict}</span>
                  </td>
                  <td className="wrap">
                    {item.formula} {item.verdict_line}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="studies">
        <h2>Studies</h2>
        <p className="dek">
          Train prints end 31 Dec 2019. Holdout starts 1 Jan 2020. Thresholds used as rules are frozen on the train window.
          The date filter above does not move these verdicts. Each study is also a notebook in the repository.
        </p>
        <div className="table-wrap">
          <table>
            <caption>{studies.studies.length} studies</caption>
            <thead>
              <tr>
                <th>#</th>
                <th>Study</th>
                <th>Verdict</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {studies.studies.map((study) => (
                <tr key={study.slug}>
                  <td>{study.index}</td>
                  <td>
                    <a href={`#study-${study.slug}`}>{study.title}</a>
                  </td>
                  <td>
                    <span className={`verdict ${study.verdict}`}>{study.verdict}</span>
                  </td>
                  <td className="wrap">{study.verdict_line}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {studies.studies.map((study) => (
          <article key={study.slug} className="cell" id={`study-${study.slug}`}>
            <h3>
              {study.index} {study.title}
            </h3>
            <p className={`verdict ${study.verdict}`}>{study.verdict}</p>
            <p>{study.question}</p>
            {study.formula ? <p>{study.formula}</p> : null}
            <p>{study.verdict_line}</p>
            <p>
              <a href={`/notebooks/${study.index}-${study.slug}.ipynb`}>Notebook {study.index}-{study.slug}.ipynb</a>
            </p>
            <StudyChart chart={study.chart} />
            <div className="table-wrap">
              <table>
                <caption>{study.table.caption}</caption>
                <thead>
                  <tr>
                    {study.table.columns.map((column) => (
                      <th key={column}>{column}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {study.table.rows.map((row) => (
                    <tr key={row.join("|")}>
                      {row.map((cell, index) => (
                        <td key={`${index}-${cell}`}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </article>
        ))}
      </section>

      <section id="notes">
        <h2>Notes</h2>
        {notes.map((note) => (
          <article key={note.id} id={note.id} className="cell">
            <h3>
              <Link href={`/#${note.id}`}>{note.title}</Link>
            </h3>
            {note.body.map((paragraph) => (
              <p key={paragraph}>{paragraph}</p>
            ))}
          </article>
        ))}
      </section>

      <section id="faq">
        <h2>Questions the file can answer</h2>
        {questions.map((item) => (
          <article key={item.q} className="cell">
            <h3>{item.q}</h3>
            <p>{item.a}</p>
          </article>
        ))}
      </section>

      <section id="sources">
        <h2>Sources and downloads</h2>
        <p className="dek">
          EIA, FRED, and the CFTC files are US government works. The code around them is MIT.
          A derived series names its inputs. Retrieval for this snapshot: {catalog.retrieved_at}.
        </p>
        <ul className="downloads">
          {downloads.map(([file, label]) => (
            <li key={file}>
              <a href={`/downloads/${file}`}>{label}</a>
            </li>
          ))}
        </ul>
        <div className="table-wrap">
          <table>
            <caption>Series in this snapshot</caption>
            <thead>
              <tr>
                <th>Id</th>
                <th>Source</th>
                <th>Count</th>
                <th>Last date</th>
                <th>Last value</th>
                <th>Retrieved</th>
              </tr>
            </thead>
            <tbody>
              {catalog.series.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>
                    {item.source_url ? <a href={item.source_url}>{item.derived ? "Derived" : item.source}</a> : item.derived ? "Derived" : item.source}
                  </td>
                  <td>{item.count}</td>
                  <td>{item.end}</td>
                  <td>{item.last_value}</td>
                  <td>{item.retrieved_at.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="table-wrap">
          <table>
            <caption>Linked, not copied</caption>
            <thead>
              <tr>
                <th>Source</th>
                <th>Why it is a link</th>
              </tr>
            </thead>
            <tbody>
              {linked.map(([name, href, why]) => (
                <tr key={href}>
                  <td>
                    <a href={href}>{name}</a>
                  </td>
                  <td className="wrap">{why}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="changelog">
        <h2>Changelog</h2>
        {latest ? (
          <>
            <p>
              {latest.summary} The machine-readable log is data/changelog.json. A failed validation does not add a row.
            </p>
            <div className="table-wrap">
              <table>
                <caption>Latest refresh, {latest.retrieved_at}</caption>
                <thead>
                  <tr>
                    <th>Series</th>
                    <th>Now</th>
                  </tr>
                </thead>
                <tbody>
                  {latest.changes.slice(0, 12).map((change) => (
                    <tr key={change.id}>
                      <td>{change.id}</td>
                      <td>{change.after || change.before}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p>No refresh has been recorded.</p>
        )}
      </section>
    </>
  );
}
