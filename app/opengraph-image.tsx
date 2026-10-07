import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "Crude oil archive. EIA, FRED, CFTC.";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#000",
          color: "#fff",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "64px",
          fontFamily: "ui-monospace, monospace",
        }}
      >
        <div style={{ fontSize: 22, letterSpacing: 4 }}>CRUDE OIL</div>
        <div style={{ fontSize: 68, lineHeight: 0.95, letterSpacing: -2, maxWidth: 900 }}>
          The print, with the file still attached.
        </div>
        <div style={{ fontSize: 22 }}>EIA, FRED, CFTC. Retrieved with the source on the row.</div>
      </div>
    ),
    { ...size },
  );
}
