(() => {
  if (window.__demo) return
  const css = `
  #demo-layer{position:fixed;inset:0;pointer-events:none;z-index:2147483000;font-family:'IBM Plex Sans',ui-sans-serif,system-ui,sans-serif}
  #demo-dim{position:fixed;inset:0;background:rgba(10,20,15,.38);opacity:0;transition:opacity .45s ease}
  #demo-ring{position:fixed;border:2.5px solid #f5b400;border-radius:10px;box-shadow:0 0 0 5px rgba(245,180,0,.22),0 0 24px rgba(245,180,0,.35);opacity:0;transition:all .5s cubic-bezier(.2,.8,.2,1)}
  #demo-ring.dim{box-shadow:0 0 0 5px rgba(245,180,0,.22),0 0 0 200vmax rgba(10,20,15,.38)}
  #demo-callout{position:fixed;max-width:340px;background:#0f6b43;color:#fff;font-size:15px;line-height:1.45;padding:12px 16px;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.25);opacity:0;transform:translateY(6px);transition:opacity .4s ease,transform .4s ease}
  #demo-callout.show{opacity:1;transform:none}
  #demo-callout::after{content:'';position:absolute;width:12px;height:12px;background:#0f6b43;transform:rotate(45deg)}
  #demo-callout[data-side=right]::after{left:-6px;top:calc(50% - 6px)}
  #demo-callout[data-side=left]::after{right:-6px;top:calc(50% - 6px)}
  #demo-callout[data-side=bottom]::after{top:-6px;left:calc(50% - 6px)}
  #demo-callout[data-side=top]::after{bottom:-6px;left:calc(50% - 6px)}
  #demo-caption{position:fixed;left:50%;bottom:34px;transform:translate(-50%,10px);background:rgba(28,30,29,.92);color:#fff;font-size:15px;padding:9px 20px;border-radius:999px;opacity:0;transition:opacity .4s ease,transform .4s ease;white-space:nowrap}
  #demo-caption.show{opacity:1;transform:translate(-50%,0)}
  #demo-card{position:fixed;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;color:#fff;background:radial-gradient(ellipse at 30% 20%,#123a63 0%,#0a1a33 45%,#050914 100%);opacity:0;transition:opacity .6s ease;padding:0 15%}
  #demo-card.show{opacity:1}
  #demo-card .k{font-size:15px;letter-spacing:.35em;opacity:.8;margin-bottom:14px}
  #demo-card .t{font-size:50px;font-weight:600;letter-spacing:-.01em;margin-bottom:18px}
  #demo-card .s{font-size:20px;opacity:.9;line-height:1.5;max-width:900px}
  #demo-card .logo{display:flex;align-items:center;gap:14px;margin-bottom:26px}
  #demo-card .logo span{width:58px;height:58px;border-radius:14px;background:#38bdf8;display:flex;align-items:center;justify-content:center}
  #demo-cursor{position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483600;transition:transform .7s cubic-bezier(.3,.7,.2,1);will-change:transform}
  #demo-cursor .dot{position:absolute;left:-14px;top:-14px;width:28px;height:28px;border-radius:50%;background:rgba(245,180,0,.45);transform:scale(0);transition:transform .18s ease,opacity .35s ease;opacity:0}
  #demo-cursor.click .dot{transform:scale(1);opacity:1}
  `
  const bolt = '<svg width="32" height="32" viewBox="0 0 24 24" fill="#050914"><path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/></svg>'
  const arrow = '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M4 2l15 11.5-6.6.9 3.9 7.6-3 1.5-3.9-7.7L4 20z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>'
  let layer, ring, callout, caption, card, cursor, pos = { x: 800, y: 450 }
  function mount() {
    if (document.getElementById('demo-layer')) return
    const style = document.createElement('style')
    style.textContent = css
    document.documentElement.appendChild(style)
    layer = document.createElement('div')
    layer.id = 'demo-layer'
    layer.innerHTML = `<div id="demo-dim"></div><div id="demo-ring"></div><div id="demo-callout"></div><div id="demo-caption"></div><div id="demo-card"></div><div id="demo-cursor">${arrow}<div class="dot"></div></div>`
    document.documentElement.appendChild(layer)
    ring = layer.querySelector('#demo-ring')
    callout = layer.querySelector('#demo-callout')
    caption = layer.querySelector('#demo-caption')
    card = layer.querySelector('#demo-card')
    cursor = layer.querySelector('#demo-cursor')
    const saved = sessionStorage.getItem('demo-cursor')
    if (saved) pos = JSON.parse(saved)
    cursor.style.transition = 'none'
    cursor.style.transform = `translate(${pos.x}px,${pos.y}px)`
    requestAnimationFrame(() => (cursor.style.transition = ''))
  }
  function rectOf(target, pad) {
    const el = typeof target === 'string' ? document.querySelector(target) : target
    if (!el) return null
    const r = el.getBoundingClientRect()
    return { x: r.left - pad, y: r.top - pad, w: r.width + pad * 2, h: r.height + pad * 2 }
  }
  function placeCallout(r, side) {
    const c = callout.getBoundingClientRect()
    const gap = 16, vw = innerWidth, vh = innerHeight
    if (side === 'auto') side = r.x + r.w + gap + c.width < vw - 10 ? 'right' : r.x - gap - c.width > 10 ? 'left' : r.y + r.h + gap + c.height < vh ? 'bottom' : 'top'
    let x, y
    if (side === 'right') { x = r.x + r.w + gap; y = r.y + r.h / 2 - c.height / 2 }
    if (side === 'left') { x = r.x - gap - c.width; y = r.y + r.h / 2 - c.height / 2 }
    if (side === 'bottom') { x = r.x + r.w / 2 - c.width / 2; y = r.y + r.h + gap }
    if (side === 'top') { x = r.x + r.w / 2 - c.width / 2; y = r.y - gap - c.height }
    x = Math.max(12, Math.min(vw - c.width - 12, x))
    y = Math.max(12, Math.min(vh - c.height - 12, y))
    callout.dataset.side = side
    callout.style.left = x + 'px'
    callout.style.top = y + 'px'
  }
  window.__demo = {
    mount,
    focus(target, text, opts = {}) {
      mount()
      const r = opts.rect || rectOf(target, opts.pad ?? 6)
      if (!r) return false
      ring.classList.toggle('dim', opts.dim !== false)
      Object.assign(ring.style, { left: r.x + 'px', top: r.y + 'px', width: r.w + 'px', height: r.h + 'px', opacity: 1, borderRadius: (opts.radius ?? 10) + 'px' })
      if (text) {
        callout.classList.remove('show')
        callout.style.maxWidth = (opts.width || 340) + 'px'
        callout.textContent = text
        requestAnimationFrame(() => { placeCallout(r, opts.side || 'auto'); callout.classList.add('show') })
      } else callout.classList.remove('show')
      return true
    },
    clear() {
      mount()
      ring.style.opacity = 0
      ring.classList.remove('dim')
      callout.classList.remove('show')
    },
    caption(text) {
      mount()
      if (!text) return caption.classList.remove('show')
      caption.textContent = text
      caption.classList.add('show')
    },
    card(kicker, title, sub, logo) {
      mount()
      card.innerHTML = (logo ? `<div class="logo"><span>${bolt}</span></div>` : '') + (kicker ? `<div class="k">${kicker}</div>` : '') + `<div class="t">${title}</div>` + (sub ? `<div class="s">${sub}</div>` : '')
      card.classList.add('show')
    },
    hideCard() { mount(); card.classList.remove('show') },
    move(x, y, ms) {
      mount()
      cursor.style.transitionDuration = (ms ?? 700) + 'ms'
      cursor.style.transform = `translate(${x}px,${y}px)`
      pos = { x, y }
      sessionStorage.setItem('demo-cursor', JSON.stringify(pos))
    },
    click() {
      mount()
      cursor.classList.add('click')
      setTimeout(() => cursor.classList.remove('click'), 380)
    },
    hideCursor(hidden) { mount(); cursor.style.opacity = hidden ? 0 : 1 },
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
  else mount()
})()
