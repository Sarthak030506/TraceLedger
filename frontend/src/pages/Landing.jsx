import React, { useEffect, useState } from 'react';
import { ChevronRight, Github, Terminal, Database, KeyRound, Link2, ShieldCheck } from 'lucide-react';
import { Link } from '../router';
import { Wordmark, Selected, SealGlyph, Reveal, PrincipleQuote } from '../components/brand';
import {
  HeroPanel, SealIllustration, TreeIllustration, AnchorIllustration,
  TerminalMock, TamperBento, CodeBento, ChainBento, CtaWatermark,
} from '../components/landing/Illustrations';
import { fetchHealth } from '../services/api';

const REPO = 'https://github.com/Sarthak030506/TraceLedger';

function TopNav() {
  return (
    <header className="absolute inset-x-0 top-0 z-30">
      <div className="shell flex h-[72px] items-center justify-between">
        <Link to="/" className="text-paper" aria-label="TraceLedger home"><Wordmark /></Link>
        <nav className="flex items-center gap-5 text-[14px] text-paper/75 sm:gap-7">
          <a href="#how" className="hidden transition-colors hover:text-paper sm:inline">How it works</a>
          <a href="#verify" className="hidden transition-colors hover:text-paper sm:inline">Verify</a>
          <a href={REPO} target="_blank" rel="noreferrer" className="hidden transition-colors hover:text-paper sm:inline">Docs</a>
          <span className="hidden h-4 w-px bg-white/20 sm:block" />
          <Link to="/app" className="transition-colors hover:text-paper">Open dashboard</Link>
        </nav>
      </div>
    </header>
  );
}

function LiveChip({ health }) {
  if (!health) return <span className="h-[30px]" />;
  const live = !health.is_fallback && health.status === 'ok';
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 font-mono text-[11.5px] text-paper/70">
      <span className={`h-1.5 w-1.5 rounded-full ${live && health.blockchain_connected ? 'bg-paper' : 'bg-white/30'}`} />
      {live
        ? `${health.anchor_mode === 'live' ? 'Live on MST testnet' : `Mode: ${health.anchor_mode}`} · ${health.total_batches} batches anchored`
        : 'Backend offline · preview mode'}
    </span>
  );
}

function Hero({ health }) {
  return (
    <section className="relative overflow-hidden bg-ink pb-24 pt-[140px] sm:pt-[170px]">
      <div className="pointer-events-none absolute inset-0" aria-hidden="true"
        style={{ background: 'radial-gradient(60% 50% at 50% 28%, rgba(255,255,255,0.07), transparent 70%), radial-gradient(40% 35% at 50% 78%, rgba(255,255,255,0.05), transparent 70%)' }} />
      <div className="shell relative text-center">
        <div className="animate-fade-up"><LiveChip health={health} /></div>
        <h1 className="display mt-8 animate-fade-up text-[46px] text-paper [animation-delay:80ms] sm:text-[76px] md:text-[92px]">
          Trust the <Selected>evidence</Selected>,
          <br />
          not the serv<SealGlyph label="e" />r
        </h1>
        <p className="mx-auto mt-7 max-w-[560px] animate-fade-up text-[17px] leading-relaxed text-muted-dark [animation-delay:160ms] sm:text-[19px]">
          TraceLedger seals security events into Merkle batches and anchors them on MST Blockchain,
          so anyone can prove a log was never altered, deleted or reordered.
        </p>
        <div className="mt-10 animate-fade-up [animation-delay:240ms]">
          <Link to="/app" className="btn-light">Get started <ChevronRight className="h-4 w-4" /></Link>
        </div>
      </div>
      <div className="relative mt-16 animate-fade-up px-3 [animation-delay:320ms] sm:mt-20 sm:px-6">
        <HeroPanel health={health} />
      </div>
    </section>
  );
}

function PrimitivesStrip() {
  const marks = ['SHA-256', 'Merkle trees', 'Ed25519', 'MST Blockchain', 'Solidity', 'FastAPI', 'SQLite'];
  return (
    <section className="bg-ink pb-24">
      <div className="shell text-center">
        <p className="text-[14px] text-muted-dark">Built on open, auditable primitives — nothing proprietary to trust</p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 sm:gap-x-14">
          {marks.map((m) => (
            <span key={m} className="text-[19px] font-semibold tracking-[-0.02em] text-white/40 sm:text-[21px]">{m}</span>
          ))}
        </div>
      </div>
    </section>
  );
}

function FeatureRow({ title, children, art, delay }) {
  return (
    <Reveal delay={delay} className="grid items-start gap-8 md:grid-cols-[0.42fr_0.58fr] md:gap-12">
      {art}
      <div className="md:pt-8">
        <h3 className="display text-[34px] text-ink sm:text-[40px]">{title}</h3>
        <p className="mt-4 max-w-[340px] text-[17px] leading-[1.55] text-muted-light">{children}</p>
      </div>
    </Reveal>
  );
}

function HowItWorks() {
  return (
    <section id="how" className="scroll-mt-10 bg-paper py-[120px] text-ink sm:py-[140px]">
      <div className="shell">
        <PrincipleQuote label="Design principle 01">
          “A log you can’t verify is just a story the server tells you.”
        </PrincipleQuote>

        <Reveal className="mt-[120px] sm:mt-[150px]">
          <h2 className="display max-w-[620px] text-[44px] sm:text-[60px]">Turn any log stream into evidence</h2>
          <p className="mt-5 max-w-[440px] text-[18px] leading-[1.5] text-muted-light">
            One pipeline from the moment an event happens to the moment an auditor checks it.
          </p>
        </Reveal>

        <div className="mt-20 space-y-20 sm:space-y-24">
          <FeatureRow title="Sealed at the source" art={<SealIllustration />}>
            A sidecar validates each event, strips secrets and masks personal data, then assigns a gap-free sequence number and a SHA-256 hash.
          </FeatureRow>
          <FeatureRow title="Batched into one root" art={<TreeIllustration />}>
            Record hashes fold into a Merkle tree. Change one byte of one event and the root changes with it.
          </FeatureRow>
          <FeatureRow
            title={<><Selected tone="light">Anchored</Selected> on-chain</>}
            art={<AnchorIllustration />}
          >
            Each root is committed to a TraceLedger contract on MST Blockchain, chained to the batch before it, so history can’t be quietly rewritten.
          </FeatureRow>
        </div>
      </div>
    </section>
  );
}

function VerifyBand() {
  const tools = [
    { icon: Terminal, label: 'REST API' },
    { icon: Database, label: 'Sidecar store' },
    { icon: Link2, label: 'Contract reads' },
    { icon: KeyRound, label: 'Ed25519' },
    { icon: ShieldCheck, label: 'Inclusion proofs' },
  ];
  return (
    <section id="verify" className="scroll-mt-10 bg-ink py-[120px] text-paper sm:py-[140px]">
      <div className="shell">
        <Reveal className="grid items-center gap-10 md:grid-cols-[0.46fr_0.54fr] md:gap-14">
          <TerminalMock />
          <div>
            <h2 className="display text-[40px] sm:text-[48px]">Verify without trusting us</h2>
            <p className="mt-4 max-w-[380px] text-[17px] leading-[1.55] text-muted-dark">
              Re-hash the raw records, rebuild the root and compare it with the commitment read straight from the contract.
              Every response says exactly what was checked.
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-5">
              {tools.map(({ icon: Icon, label }) => (
                <span key={label} title={label} className="text-paper/70">
                  <Icon className="h-[22px] w-[22px]" aria-label={label} />
                </span>
              ))}
            </div>
          </div>
        </Reveal>

        <div className="mt-[120px] text-paper sm:mt-[140px]">
          <PrincipleQuote tone="dark" label="Design principle 02">
            “If anchoring fails, we say so. A fake confirmation is worse than none.”
          </PrincipleQuote>
        </div>
      </div>
    </section>
  );
}

function BentoCard({ title, children, art, className = '' }) {
  return (
    <Reveal className={`flex flex-col overflow-hidden rounded-card hairline-light bg-white ${className}`}>
      <div className="m-2 flex-1 overflow-hidden rounded-[16px] bg-paper-card">{art}</div>
      <div className="px-7 pb-7 pt-5">
        <h3 className="text-[22px] font-medium tracking-[-0.02em] text-ink">{title}</h3>
        <p className="mt-2 max-w-[380px] text-[15px] leading-[1.55] text-muted-light">{children}</p>
      </div>
    </Reveal>
  );
}

function Bento() {
  return (
    <section className="bg-paper py-[120px] text-ink sm:py-[140px]">
      <div className="shell">
        <Reveal>
          <h2 className="display max-w-[560px] text-[44px] sm:text-[60px]">Built for how security teams already work</h2>
        </Reveal>
        <div className="mt-16 grid gap-6 md:grid-cols-[1.5fr_1fr]">
          <BentoCard title="Catches every kind of tampering" art={<TamperBento />}>
            Altered, deleted, reordered and replayed records each leave a distinct trace, and the report names the exact sequence numbers.
          </BentoCard>
          <div className="grid gap-6">
            <BentoCard title="One HTTP call to ingest" art={<CodeBento />}>
              Apps post events to an authenticated local receiver. No SDK required.
            </BentoCard>
            <BentoCard title="Every batch, one chain" art={<ChainBento />}>
              Each commitment carries the previous root, so gaps and rewrites show up immediately.
            </BentoCard>
          </div>
        </div>

        <div className="mt-[120px] sm:mt-[150px]">
          <Reveal as="figure" className="mx-auto max-w-[860px] text-center">
            <blockquote className="text-[28px] font-medium leading-[1.2] tracking-[-0.02em] sm:text-[40px]">
              <span className="text-[#8b8f99]">“TraceLedger detects tampering; it doesn’t prevent it. </span>
              <span className="text-ink">That honesty is what makes the evidence worth trusting.”</span>
            </blockquote>
            <figcaption className="mt-8 font-mono text-[12px] text-muted-light">DESIGN PRINCIPLE 03</figcaption>
          </Reveal>
        </div>

        <Reveal className="relative mt-[120px] overflow-hidden rounded-[24px] bg-ink px-8 py-20 text-paper sm:px-16 sm:py-24">
          <CtaWatermark />
          <h2 className="display relative text-[42px] sm:text-[60px]">Put your logs<br />on the record</h2>
          <div className="relative mt-10 flex flex-wrap gap-3">
            <Link to="/app" className="btn-accent">Get started <ChevronRight className="h-4 w-4" /></Link>
            <Link to="/app/lab" className="btn-ghost-dark">Try the tamper lab</Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="bg-ink py-10 text-[14px] text-muted-dark">
      <div className="shell flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap items-center gap-x-7 gap-y-3">
          <Wordmark className="text-paper" />
          <Link to="/app" className="hover:text-paper">Dashboard</Link>
          <Link to="/app/verify" className="hover:text-paper">Verify</Link>
          <Link to="/app/lab" className="hover:text-paper">Tamper lab</Link>
          <a href={`${REPO}#readme`} target="_blank" rel="noreferrer" className="hover:text-paper">Docs</a>
        </div>
        <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
          <a href={REPO} target="_blank" rel="noreferrer" aria-label="GitHub repository" className="hover:text-paper">
            <Github className="h-4 w-4" />
          </a>
          <span>© 2026 TraceLedger</span>
          <span className="font-mono text-[12px]">Built for the MST Blockchain Buildathon</span>
        </div>
      </div>
    </footer>
  );
}

export default function Landing() {
  const [health, setHealth] = useState(null);
  useEffect(() => { fetchHealth().then(setHealth).catch(() => setHealth(null)); }, []);
  return (
    <div className="relative bg-ink">
      <TopNav />
      <main>
        <Hero health={health} />
        <PrimitivesStrip />
        <HowItWorks />
        <VerifyBand />
        <Bento />
      </main>
      <Footer />
    </div>
  );
}
