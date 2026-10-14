import type {NextConfig} from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Windows can reject concurrent writes to newly-created nested chunk folders.
  // A single in-process compiler keeps local and CI builds deterministic.
  experimental: {
    cpus: 1,
    webpackBuildWorker: false,
  },
};

export default nextConfig;

