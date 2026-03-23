// Initialize theme from localStorage before paint to prevent flash
(function() {
    const theme = localStorage.getItem('alluci_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
})();
