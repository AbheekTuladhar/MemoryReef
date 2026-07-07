export type FishKind = "dory" | "nemo" | "puffer";

// Lightweight cartoon reef fish drawn as a few inline SVG paths each, sized ~34px.
// Used as the avatars on the learning-loop steps. `bob` adds a gentle wiggle
// (see .fishBob in styles.css) while a step is actively thinking.
export function Fish({ kind, bob = false }: { kind: FishKind; bob?: boolean }) {
  return (
    <span className={`fish fish-${kind}${bob ? " fishBob" : ""}`} aria-hidden="true">
      {kind === "dory" && <Dory />}
      {kind === "nemo" && <Nemo />}
      {kind === "puffer" && <Puffer />}
    </span>
  );
}

// Dory — blue tang: blue body, yellow tail, dark royal-blue back accent.
function Dory() {
  return (
    <svg viewBox="0 0 40 32" width="34" height="34" role="img">
      <path d="M27 16 L40 7 L40 25 Z" fill="#ffd23f" stroke="#0b2230" strokeWidth="1.4" strokeLinejoin="round" />
      <ellipse cx="17" cy="16" rx="14" ry="9.5" fill="#2f86e0" stroke="#0b2230" strokeWidth="1.4" />
      <path d="M5 15 Q13 3 25 9 Q27 12 27 15 Q16 12 5 18 Z" fill="#123a6b" opacity="0.85" />
      <path d="M15 25 Q19 30 24 26 Q20 24 15 25 Z" fill="#2f86e0" stroke="#0b2230" strokeWidth="1.2" strokeLinejoin="round" />
      <circle cx="10" cy="15" r="2.6" fill="#0b1f33" />
      <circle cx="9" cy="14.2" r="0.9" fill="#ffffff" />
    </svg>
  );
}

// Nemo — clownfish: orange body, white bands with dark edges, black-tipped fins.
function Nemo() {
  return (
    <svg viewBox="0 0 40 32" width="34" height="34" role="img">
      <path d="M28 16 L40 8 L40 24 Z" fill="#ff8127" stroke="#0b2230" strokeWidth="1.4" strokeLinejoin="round" />
      <ellipse cx="18" cy="16" rx="14" ry="9.5" fill="#ff8127" stroke="#0b2230" strokeWidth="1.4" />
      <path d="M13 7.5 Q11 16 13 24.5 L16 24 Q14.2 16 16 8 Z" fill="#fff5ec" stroke="#0b2230" strokeWidth="1" />
      <path d="M24 9.5 Q22.6 16 24 22.5 L26.5 21.5 Q25.4 16 26.5 10.5 Z" fill="#fff5ec" stroke="#0b2230" strokeWidth="1" />
      <path d="M16 24 Q19 29 24 25 Q20 23 16 24 Z" fill="#ff8127" stroke="#0b2230" strokeWidth="1.2" strokeLinejoin="round" />
      <circle cx="10" cy="15" r="2.6" fill="#0b1f33" />
      <circle cx="9" cy="14.2" r="0.9" fill="#ffffff" />
    </svg>
  );
}

// Puffer — round pufferfish: yellow ball, little spikes, tiny tail.
function Puffer() {
  return (
    <svg viewBox="0 0 40 32" width="34" height="34" role="img">
      <g fill="#f4b62c" stroke="#0b2230" strokeWidth="1.2" strokeLinejoin="round">
        <path d="M31 16 L38 11 L37 16 L38 21 Z" />
        <path d="M20 3 L23 8 L17 8 Z" />
        <path d="M20 29 L23 24 L17 24 Z" />
        <path d="M7 8 L12 11 L9 12 Z" />
        <path d="M7 24 L12 21 L9 20 Z" />
      </g>
      <circle cx="19" cy="16" r="12" fill="#ffd23f" stroke="#0b2230" strokeWidth="1.4" />
      <circle cx="13" cy="14" r="3" fill="#0b1f33" />
      <circle cx="11.7" cy="13" r="1" fill="#ffffff" />
      <path d="M9 20 Q13 23 17 20" fill="none" stroke="#0b2230" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="24" cy="19" r="1.4" fill="#e79a1a" />
      <circle cx="22" cy="12" r="1.2" fill="#e79a1a" />
    </svg>
  );
}
