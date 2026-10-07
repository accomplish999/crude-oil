import Link from "next/link";

export default function NotFound() {
  return (
    <>
      <p className="kicker">404</p>
      <h1>That page is not in the archive.</h1>
      <p className="dek">
        <Link href="/">Back to the front</Link>
      </p>
    </>
  );
}
