import React, { useEffect, useRef } from 'react';

/** Mark: a ledger "T" whose stem ends in a sealed node. */
export function LogoMark({ className = 'h-5 w-5' }) {
  return (
    <svg viewBox="0 0 32 32" fill="none" className={className} aria-hidden="true">
      <path d="M6 9.5h20M16 9.5v13" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <circle cx="24" cy="23" r="3" fill="currentColor" />
    </svg>
  );
}

export function Wordmark({ className = '' }) {
  return (
    <span className={`inline-flex items-center gap-2 text-[17px] font-semibold tracking-[-0.02em] ${className}`}>
      <LogoMark className="h-[18px] w-[18px]" />
      TraceLedger
    </span>
  );
}

/** Dashed "selection box" with corner handles, wrapped around a word. */
export function Selected({ children, tone = 'dark', className = '' }) {
  const line = tone === 'dark' ? 'border-white/70' : 'border-accent/70';
  const handle = tone === 'dark' ? 'bg-ink border-white' : 'bg-white border-accent';
  return (
    <span className={`relative inline-block px-[0.12em] ${className}`}>
      <span className={`pointer-events-none absolute inset-0 border border-dashed ${line}`} aria-hidden="true" />
      {['-left-[4px] -top-[4px]', '-right-[4px] -top-[4px]', '-left-[4px] -bottom-[4px]', '-right-[4px] -bottom-[4px]'].map((pos) => (
        <span key={pos} className={`pointer-events-none absolute h-[8px] w-[8px] border ${handle} ${pos}`} aria-hidden="true" />
      ))}
      <span className="relative">{children}</span>
    </span>
  );
}

/** Seal glyph that replaces a letter inside a display word. */
export function SealGlyph({ label = 'e' }) {
  const rays = Array.from({ length: 12 }, (_, i) => i * 30);
  return (
    <span className="relative inline-block w-[0.62em] align-baseline" role="img" aria-label={label}>
      <svg viewBox="0 0 40 40" className="absolute bottom-[0.02em] left-0 h-[0.62em] w-[0.62em]" aria-hidden="true">
        {rays.map((deg) => (
          <line key={deg} x1="20" y1="20" x2="20" y2="3" stroke="currentColor" strokeWidth="3.4" strokeLinecap="round"
            transform={`rotate(${deg} 20 20)`} />
        ))}
      </svg>
      <span className="invisible">{label}</span>
    </span>
  );
}

/** Soft fade-up on first scroll into view. */
export function Reveal({ as: Tag = 'div', delay = 0, className = '', children, ...rest }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    if (!('IntersectionObserver' in window)) {
      el.classList.add('is-visible');
      return undefined;
    }
    const io = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        el.classList.add('is-visible');
        io.disconnect();
      }
    }, { rootMargin: '0px 0px -10% 0px' });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <Tag ref={ref} data-reveal="" style={delay ? { transitionDelay: `${delay}ms` } : undefined} className={className} {...rest}>
      {children}
    </Tag>
  );
}

/** Quote used as a rhythm break between heavy sections. */
export function PrincipleQuote({ children, label, tone = 'light' }) {
  const sub = tone === 'light' ? 'text-muted-light' : 'text-muted-dark';
  const chip = tone === 'light' ? 'bg-ink text-paper' : 'bg-paper text-ink';
  return (
    <Reveal as="figure" className="mx-auto max-w-[820px] text-center">
      <blockquote className="text-[28px] font-medium leading-[1.2] tracking-[-0.02em] sm:text-[40px]">
        {children}
      </blockquote>
      <figcaption className="mt-8 inline-flex items-center gap-3 text-left">
        <span className={`grid h-10 w-10 place-items-center rounded-full ${chip}`}>
          <LogoMark className="h-[18px] w-[18px]" />
        </span>
        <span>
          <span className="block text-[15px] font-medium">TraceLedger</span>
          <span className={`block font-mono text-[12px] ${sub}`}>{label}</span>
        </span>
      </figcaption>
    </Reveal>
  );
}
