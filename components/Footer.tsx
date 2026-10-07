export function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <p>
          Past prices do not predict future prices. This is not financial
          advice. A futures contract can wipe out the account that trades it.
        </p>
        <div className="links">
          <a href="https://github.com/accomplish999/crude-oil">Repository</a>
          <a href="https://www.eia.gov/petroleum/supply/weekly/">EIA WPSR</a>
          <a href="https://www.cftc.gov/dea/newcot/c_disagg.txt">CFTC COT</a>
          <a href="https://accompli.sh/">accompli.sh</a>
        </div>
      </div>
    </footer>
  );
}
