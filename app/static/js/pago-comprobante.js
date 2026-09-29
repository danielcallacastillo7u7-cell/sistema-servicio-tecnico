(() => {
  const dialog = document.getElementById('pagoComprobante');
  const frame = document.getElementById('pagoComprobanteMarco');
  const print = document.getElementById('pagoComprobanteImprimir');
  let previousFocus, overflow;
  function open(url) {
    const target = new URL(url, location.origin);
    if (target.origin !== location.origin || !/^\/pagos-internet\/\d+\/ticket$/.test(target.pathname)) return;
    document.getElementById('pagoComprobantePDF').href = target.pathname.replace(/ticket$/, 'pdf');
    previousFocus = document.activeElement;
    target.searchParams.set('embed', '1');
    print.disabled = true;
    frame.src = target.href;
    if (!dialog.open) {
      overflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      dialog.showModal();
    }
  }
  frame.addEventListener('load', () => {
    print.disabled = !frame.contentDocument?.querySelector('.ticket');
  });
  print.addEventListener('click', () => frame.contentWindow.print());
  dialog.querySelectorAll('[data-cerrar-pago]').forEach(button => button.addEventListener('click', () => dialog.close()));
  dialog.addEventListener('click', event => {
    const box = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => {
    document.body.style.overflow = overflow;
    previousFocus?.focus();
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('a[data-pago-ticket]');
    if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    open(link.href);
  });
  window.ServiPagoComprobante = {open};
})();
