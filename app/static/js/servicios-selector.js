(() => {
    const selector = document.querySelector('.services-mode-slider');
    const form = document.querySelector('#ordenForm, #installationForm');
    if (!selector || !form) return;
    let edited = false;
    form.addEventListener('input', () => { edited = true; });
    form.addEventListener('change', () => { edited = true; });
    selector.addEventListener('click', event => {
        const link = event.target.closest('a');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        if (link.hasAttribute('aria-current')) { event.preventDefault(); return; }
        const savedInstallation = form.id === 'installationForm' && document.querySelector('#saveInstallation')?.disabled;
        if (edited && !savedInstallation && !confirm('Hay datos sin guardar. ¿Quieres cambiar de servicio y descartarlos?')) {
            event.preventDefault(); return;
        }
        selector.classList.toggle('is-installations', link.pathname === '/camaras');
    });
})();
