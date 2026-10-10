(() => {
  const date = document.getElementById('dashboardToday');
  if (date) date.textContent = new Intl.DateTimeFormat('es-PE', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'America/Lima'
  }).format(new Date());

  document.addEventListener('keydown', event => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault();
      document.getElementById('buscadorGlobal')?.focus();
    }
  });

  // Decorative curves from the visual reference, not historical statistics.
  const colors = ['#b365ff', '#aa70ff', '#2495ff', '#ff678b', '#389fff', '#ffb319', '#15c994', '#ff6685'];
  const cards = document.querySelectorAll('.home-total, .home-status, .home-canceled');
  cards.forEach((card, index) => {
    const color = colors[index % colors.length];
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.classList.add('dashboard-spark');
    svg.setAttribute('viewBox', '0 0 100 50');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.innerHTML = `<defs><linearGradient id="spark-${index}" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${color}" stop-opacity=".42"/><stop offset="100%" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path d="M1 44 C15 45 22 13 35 23 S56 36 70 17 S87 0 99 7 L99 50 L1 50Z" fill="url(#spark-${index})"/><path d="M1 44 C15 45 22 13 35 23 S56 36 70 17 S87 0 99 7" fill="none" stroke="${color}" stroke-width="1.8"/>`;
    card.append(svg);
  });

  const icons = {
    'Orden': 'file-earmark-text', 'Cliente': 'person-fill', 'Equipo': 'laptop',
    'Estado': 'check-circle', 'Diagnóstico': 'activity', 'Fecha': 'calendar-event',
    'Instalación': 'file-earmark-text', 'Técnico': 'tools',
    'Fecha programada': 'calendar-event', 'Hora': 'clock', 'Comprobante': 'receipt',
    'Titular': 'person-fill', 'Mes pagado': 'calendar3', 'Total': 'cash-coin',
    'Fecha y hora (Perú)': 'clock'
  };
  document.querySelectorAll('.dashboard-table th').forEach(cell => {
    const name = icons[cell.textContent.trim()];
    if (!name) return;
    const icon = document.createElement('i');
    icon.className = `bi bi-${name}`;
    icon.setAttribute('aria-hidden', 'true');
    cell.prepend(icon);
  });
  document.querySelectorAll('.dashboard-table button').forEach(button => {
    if (button.textContent.trim() !== 'Ver detalles') return;
    const arrow = document.createElement('i');
    arrow.className = 'bi bi-arrow-right ms-1';
    arrow.setAttribute('aria-hidden', 'true');
    button.append(arrow);
  });
})();
