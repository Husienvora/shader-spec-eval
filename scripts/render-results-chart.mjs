// Renders assets/results-v0.3-{light,dark}.svg — the README results chart for
// the frozen run temperature-controlled-v0.3. Data is hard-coded from
// results shader-cells.primary.json (600 generations); re-derive and update if
// the study is ever re-run.
import {writeFileSync, mkdirSync} from 'node:fs';
import {dirname, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

// model, compile %, clean %, ±1 sd of clean across 10 seeds, total cost
const MODELS = [
  ['qwen3-coder', 100.0, 78.7, 4.2, '$0.04'],
  ['gemini-3.7-flash', 92.0, 74.7, 2.8, '$0.32'],
  ['grok-4.5', 98.7, 66.0, 3.8, '$0.63'],
  ['kimi-k2.7-code', 72.7, 50.7, 10.5, '$0.64'],
];

const THEMES = {
  light: {
    surface: '#fcfcfb',
    border: 'rgba(11,11,11,0.10)',
    primary: '#0b0b0b',
    secondary: '#52514e',
    muted: '#898781',
    grid: '#e1e0d9',
    baseline: '#c3c2b7',
    compiled: '#2a78d6',
    clean: '#eb6834',
  },
  dark: {
    surface: '#1a1a19',
    border: 'rgba(255,255,255,0.10)',
    primary: '#ffffff',
    secondary: '#c3c2b7',
    muted: '#898781',
    grid: '#2c2c2a',
    baseline: '#383835',
    compiled: '#3987e5',
    clean: '#d95926',
  },
};

const W = 880;
const H = 470;
const PLOT_X = 168;
const PLOT_W = 540;
const TOP = 96;
const PITCH = 76;
const BAR_H = 16;
const BAR_GAP = 3;
const FONT = `system-ui, -apple-system, 'Segoe UI', sans-serif`;

const x = pct => PLOT_X + (pct / 100) * PLOT_W;

// Bar with a 4px rounded data end and a square baseline end.
function bar(y, pct, fill) {
  const w = Math.max((pct / 100) * PLOT_W, 6);
  const r = 4;
  return `<path d="M ${PLOT_X} ${y} h ${w - r} a ${r} ${r} 0 0 1 ${r} ${r} v ${
    BAR_H - 2 * r
  } a ${r} ${r} 0 0 1 ${-r} ${r} h ${-(w - r)} z" fill="${fill}"/>`;
}

function render(theme) {
  const t = THEMES[theme];
  const parts = [];
  parts.push(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" font-family="${FONT}" role="img" aria-label="Compile rate versus full property compliance for four models">`,
    `<rect width="${W}" height="${H}" rx="12" fill="${t.surface}" stroke="${t.border}"/>`,
    `<text x="32" y="42" font-size="19" font-weight="700" fill="${t.primary}">Compiled is not the same as correct</text>`,
    `<text x="32" y="64" font-size="12.5" fill="${t.secondary}">600 generations — 4 models × 15 tasks × 10 seeds · temperature 0.7 · first attempt only</text>`,
  );

  // Legend (top right).
  const legend = [
    ['Compiled', t.compiled],
    ['Passed every property', t.clean],
  ];
  let lx = W - 32;
  for (const [label, color] of [...legend].reverse()) {
    const wText = label.length * 6.6;
    lx -= wText + 26;
    parts.push(
      `<rect x="${lx}" y="33" width="11" height="11" rx="2.5" fill="${color}"/>`,
      `<text x="${lx + 17}" y="43" font-size="12" fill="${t.secondary}">${label}</text>`,
    );
  }

  // Gridlines + tick labels.
  for (const pct of [0, 25, 50, 75, 100]) {
    const gx = x(pct);
    parts.push(
      `<line x1="${gx}" y1="${TOP - 10}" x2="${gx}" y2="${TOP + MODELS.length * PITCH - 18}" stroke="${
        pct === 0 ? t.baseline : t.grid
      }" stroke-width="1"/>`,
      `<text x="${gx}" y="${TOP + MODELS.length * PITCH + 2}" font-size="11" fill="${t.muted}" text-anchor="middle">${pct}%</text>`,
    );
  }

  MODELS.forEach(([name, compile, clean, sd, cost], i) => {
    const gy = TOP + i * PITCH;
    const yCompiled = gy;
    const yClean = gy + BAR_H + BAR_GAP;
    const midClean = yClean + BAR_H / 2;

    parts.push(
      `<text x="${PLOT_X - 14}" y="${gy + BAR_H - 2}" font-size="13.5" font-weight="600" fill="${t.primary}" text-anchor="end">${name}</text>`,
      `<text x="${PLOT_X - 14}" y="${gy + BAR_H + 15}" font-size="11" fill="${t.muted}" text-anchor="end">${cost} total</text>`,
      bar(yCompiled, compile, t.compiled),
      bar(yClean, clean, t.clean),
      `<text x="${x(compile) + 8}" y="${yCompiled + BAR_H - 4}" font-size="12" fill="${t.secondary}">${compile.toFixed(0)}%</text>`,
      // ±1 sd whisker on the compliance bar.
      `<line x1="${x(clean - sd)}" y1="${midClean}" x2="${x(clean + sd)}" y2="${midClean}" stroke="${t.secondary}" stroke-width="1.5"/>`,
      `<line x1="${x(clean - sd)}" y1="${midClean - 4}" x2="${x(clean - sd)}" y2="${midClean + 4}" stroke="${t.secondary}" stroke-width="1.5"/>`,
      `<line x1="${x(clean + sd)}" y1="${midClean - 4}" x2="${x(clean + sd)}" y2="${midClean + 4}" stroke="${t.secondary}" stroke-width="1.5"/>`,
      `<text x="${x(clean + sd) + 8}" y="${yClean + BAR_H - 4}" font-size="12" fill="${t.secondary}">${clean.toFixed(0)}% ± ${sd.toFixed(0)}</text>`,
    );
  });

  parts.push(
    `<text x="32" y="${H - 22}" font-size="11" fill="${t.muted}">Whiskers: ±1 standard deviation of the full-compliance rate across 10 seeds. "Passed every property" requires compiling and satisfying every check in the task's hidden spec.</text>`,
    `</svg>`,
  );
  return parts.join('\n');
}

mkdirSync(join(root, 'assets'), {recursive: true});
for (const theme of ['light', 'dark']) {
  const file = join(root, 'assets', `results-v0.3-${theme}.svg`);
  writeFileSync(file, render(theme));
  console.log('wrote', file);
}
