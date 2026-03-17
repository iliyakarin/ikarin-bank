/** @type {import('next').NextConfig} */
const nextConfig = {
    output: 'standalone',
    async rewrites() {
        const internalApiUrl = process.env.INTERNAL_API_URL || 'http://api:8000';
        return [
            {
                source: '/api/v1/:path*',
                destination: `${internalApiUrl}/v1/:path*`,
            },
        ];
    },
};

export default nextConfig;
