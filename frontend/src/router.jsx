import React, { useEffect, useState } from 'react';

// Minimal history-API router. Paths: "/" (landing) and "/app/*" (dashboard).

const listeners = new Set();

export function navigate(to) {
  if (to === window.location.pathname) return;
  window.history.pushState({}, '', to);
  listeners.forEach((fn) => fn(to));
  window.scrollTo({ top: 0 });
}

export function usePath() {
  const [path, setPath] = useState(window.location.pathname);
  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    listeners.add(setPath);
    window.addEventListener('popstate', onPop);
    return () => {
      listeners.delete(setPath);
      window.removeEventListener('popstate', onPop);
    };
  }, []);
  return path;
}

export function Link({ to, children, onClick, ...rest }) {
  return (
    <a
      href={to}
      onClick={(e) => {
        if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
        e.preventDefault();
        onClick?.(e);
        navigate(to);
      }}
      {...rest}
    >
      {children}
    </a>
  );
}
