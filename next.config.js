/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
}

module.exports = {
  async rewrites() {
    return [
      { 
        source: '/api/:path*',
        destination: (process.env.API_HOST||"http://127.0.0.1:8000") + '/:path*'
      },
    ]
  }
}
