tailwind.config = {
    theme: {
        extend: {
            colors: {
                void: 'var(--bg-base)',
                deep: 'var(--bg-elevated)',
                glass1: 'var(--glass-bg)',
                glass2: 'var(--glass-bg-hover)',
                manifold: 'var(--bg-base)',
                sovereign: 'var(--accent-secondary)',
                zinc: 'var(--text-secondary)',
                tension: 'var(--accent-warm)',
                agent: 'var(--accent)',
                flux: 'var(--accent-secondary)'
            },
            fontFamily: {
                mono: ['var(--font-mono)', '"JetBrains Mono"', 'monospace'],
                sans: ['var(--font-body)', 'Inter', 'sans-serif'],
                display: ['var(--font-display)', 'Inter', 'sans-serif']
            }
        }
    }
}
