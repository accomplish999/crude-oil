import type { MetadataRoute } from "next";
import { siteUrl } from "@/lib/archive";

const files = [
  "downloads/prices.csv",
  "downloads/prices.parquet",
  "downloads/weekly.csv",
  "downloads/weekly.parquet",
  "downloads/positions.csv",
  "downloads/positions.parquet",
  "downloads/catalog.csv",
];

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${siteUrl}/` },
    ...files.map((file) => ({ url: `${siteUrl}/${file}` })),
  ];
}
