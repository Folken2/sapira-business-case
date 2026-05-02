import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable standalone output for Docker
  output: 'standalone',
  webpack: (config, { isServer }) => {
    // Fix for react-plotly.js in Next.js
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
      };
    } else {
      // Server-side: handle canvas and pdfjs-dist for PDF processing
      config.resolve.fallback = {
        ...config.resolve.fallback,
        canvas: false, // We'll use dynamic import with try-catch
      };
      
      // Handle pdfjs-dist - don't try to bundle worker files
      config.resolve.alias = {
        ...config.resolve.alias,
        'pdfjs-dist/build/pdf.worker.min.mjs': false,
        'pdfjs-dist/build/pdf.worker.min.js': false,
      };
      
      // Mark pdf-to-img as external to avoid bundling issues
      // This allows it to be loaded at runtime from node_modules
      // @napi-rs/canvas should NOT be externalized - it needs to be available for pdfjs-dist
      config.externals = config.externals || [];
      if (Array.isArray(config.externals)) {
        config.externals.push('pdf-to-img');
      } else if (typeof config.externals === 'object') {
        config.externals['pdf-to-img'] = 'commonjs pdf-to-img';
      }
      
      // Ensure @napi-rs/canvas is not externalized - it needs native bindings
      // The standalone output will include it from node_modules
    }
    return config;
  },
};

export default nextConfig;
