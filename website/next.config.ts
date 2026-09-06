import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.NEXT_OUTPUT === "export" ? "export" : undefined,
  outputFileTracingRoot: path.join(__dirname),
  images: { unoptimized: true },
};

export default nextConfig;
