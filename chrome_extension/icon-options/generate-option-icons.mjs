import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

const colors = {
  ink: '#342d24',
  muted: '#776d5f',
  cream: '#faf7ef',
  paper: '#fffdf7',
  line: '#d8cebe',
  teal: '#12846f',
  tealDark: '#0a5d50',
  tealSoft: '#dff3ec',
  gold: '#c8943d',
  coral: '#d66d52',
  plum: '#65536f',
};

const iconShell = (title, body) => `<svg width="128" height="128" viewBox="0 0 128 128" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title">
  <title id="title">${title}</title>
  ${body}
</svg>
`;

const options = [
  {
    id: '01-stacked-pages',
    name: 'Stacked Pages',
    note: 'A clear saved-content metaphor: layered pages with a confident teal cover.',
    svg: iconShell('ContentStash icon option 1: Stacked Pages', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.cream}"/>
  <rect x="14.5" y="14.5" width="99" height="99" rx="23.5" stroke="${colors.line}"/>
  <rect x="34" y="28" width="55" height="70" rx="10" fill="${colors.paper}" stroke="${colors.line}" stroke-width="4"/>
  <rect x="42" y="36" width="55" height="70" rx="10" fill="${colors.tealSoft}" stroke="${colors.teal}" stroke-width="4"/>
  <rect x="50" y="44" width="55" height="70" rx="10" fill="${colors.teal}" stroke="${colors.tealDark}" stroke-width="4"/>
  <path d="M63 63H91" stroke="${colors.paper}" stroke-width="6" stroke-linecap="round"/>
  <path d="M63 78H84" stroke="${colors.paper}" stroke-width="6" stroke-linecap="round" opacity=".88"/>
  <path d="M63 93H78" stroke="${colors.paper}" stroke-width="6" stroke-linecap="round" opacity=".72"/>
`),
  },
  {
    id: '02-bookmark-stash',
    name: 'Bookmark Stash',
    note: 'Simple and extension-native: a bookmark held inside a compact archive shape.',
    svg: iconShell('ContentStash icon option 2: Bookmark Stash', `
  <rect width="128" height="128" rx="31" fill="${colors.teal}"/>
  <rect x="15" y="15" width="98" height="98" rx="21" fill="${colors.cream}" opacity=".14"/>
  <path d="M32 37C32 29.82 37.82 24 45 24H83C90.18 24 96 29.82 96 37V98C96 105.18 90.18 111 83 111H45C37.82 111 32 105.18 32 98V37Z" fill="${colors.paper}"/>
  <path d="M47 24H81V85L64 73L47 85V24Z" fill="${colors.tealDark}"/>
  <path d="M48 101H81" stroke="${colors.line}" stroke-width="6" stroke-linecap="round"/>
  <path d="M50 45H78" stroke="${colors.cream}" stroke-width="5" stroke-linecap="round" opacity=".9"/>
`),
  },
  {
    id: '03-capture-corners',
    name: 'Capture Corners',
    note: 'A browser-capture signal: four corners locking onto a saved page.',
    svg: iconShell('ContentStash icon option 3: Capture Corners', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.cream}"/>
  <path d="M42 31H29V53" stroke="${colors.teal}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M86 31H99V53" stroke="${colors.teal}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M42 97H29V75" stroke="${colors.teal}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M86 97H99V75" stroke="${colors.teal}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="44" y="36" width="40" height="56" rx="9" fill="${colors.paper}" stroke="${colors.line}" stroke-width="5"/>
  <path d="M55 55H74" stroke="${colors.ink}" stroke-width="6" stroke-linecap="round"/>
  <path d="M55 70H70" stroke="${colors.muted}" stroke-width="6" stroke-linecap="round"/>
  <circle cx="86" cy="90" r="10" fill="${colors.gold}"/>
`),
  },
  {
    id: '04-inbox-drop',
    name: 'Inbox Drop',
    note: 'Fast-save energy: content dropping into a sturdy local inbox.',
    svg: iconShell('ContentStash icon option 4: Inbox Drop', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.cream}"/>
  <path d="M35 66H49L56 78H72L79 66H93L100 96C101.45 102.213 96.734 108 90.354 108H37.646C31.266 108 26.55 102.213 28 96L35 66Z" fill="${colors.teal}" stroke="${colors.tealDark}" stroke-width="4" stroke-linejoin="round"/>
  <path d="M47 27H80L94 42V67H34V40C34 32.82 39.82 27 47 27Z" fill="${colors.paper}" stroke="${colors.line}" stroke-width="4" stroke-linejoin="round"/>
  <path d="M79 28V43H94" stroke="${colors.line}" stroke-width="4" stroke-linejoin="round"/>
  <path d="M48 52H75" stroke="${colors.ink}" stroke-width="5" stroke-linecap="round"/>
  <path d="M55 83H73" stroke="${colors.paper}" stroke-width="6" stroke-linecap="round"/>
`),
  },
  {
    id: '05-folder-spark',
    name: 'Folder Spark',
    note: 'A polished stash/folder mark with a small signal that content was captured.',
    svg: iconShell('ContentStash icon option 5: Folder Spark', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.tealSoft}"/>
  <path d="M28 47C28 40.373 33.373 35 40 35H55L65 45H90C96.627 45 102 50.373 102 57V92C102 98.627 96.627 104 90 104H38C31.925 104 27 99.075 27 93V49C27 47.895 27.895 47 29 47H28Z" fill="${colors.teal}" stroke="${colors.tealDark}" stroke-width="4" stroke-linejoin="round"/>
  <path d="M31 58H99L92 99H36L31 58Z" fill="${colors.paper}" stroke="${colors.tealDark}" stroke-width="4" stroke-linejoin="round"/>
  <path d="M82 26L86 36L96 40L86 44L82 54L78 44L68 40L78 36L82 26Z" fill="${colors.gold}"/>
  <path d="M47 77H76" stroke="${colors.ink}" stroke-width="6" stroke-linecap="round"/>
  <path d="M47 90H65" stroke="${colors.muted}" stroke-width="5" stroke-linecap="round"/>
`),
  },
  {
    id: '06-page-pin',
    name: 'Page Pin',
    note: 'A page plus location pin, useful if the product promise is “save this exact page.”',
    svg: iconShell('ContentStash icon option 6: Page Pin', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.cream}"/>
  <rect x="33" y="25" width="56" height="78" rx="12" fill="${colors.paper}" stroke="${colors.line}" stroke-width="5"/>
  <path d="M74 25V44H89" stroke="${colors.line}" stroke-width="5" stroke-linejoin="round"/>
  <path d="M47 51H68" stroke="${colors.ink}" stroke-width="6" stroke-linecap="round"/>
  <path d="M47 67H63" stroke="${colors.muted}" stroke-width="6" stroke-linecap="round"/>
  <path d="M84 61C72.954 61 64 69.954 64 81C64 96 84 109 84 109C84 109 104 96 104 81C104 69.954 95.046 61 84 61Z" fill="${colors.teal}" stroke="${colors.tealDark}" stroke-width="5" stroke-linejoin="round"/>
  <circle cx="84" cy="81" r="6.5" fill="${colors.paper}"/>
`),
  },
  {
    id: '07-vault-card',
    name: 'Vault Card',
    note: 'Most premium of the set: saved content as a protected object, not just a bookmark.',
    svg: iconShell('ContentStash icon option 7: Vault Card', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.ink}"/>
  <rect x="27" y="33" width="74" height="62" rx="15" fill="${colors.cream}" stroke="${colors.line}" stroke-width="4"/>
  <path d="M38 49H90" stroke="${colors.teal}" stroke-width="9" stroke-linecap="round"/>
  <path d="M43 67H70" stroke="${colors.ink}" stroke-width="6" stroke-linecap="round"/>
  <path d="M43 80H62" stroke="${colors.muted}" stroke-width="5" stroke-linecap="round"/>
  <circle cx="86" cy="76" r="13" fill="${colors.teal}"/>
  <path d="M81 76L85 80L92 72" stroke="${colors.paper}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
`),
  },
  {
    id: '08-link-stack',
    name: 'Link Stack',
    note: 'Best for “save from anywhere”: link capture plus stacked-content memory.',
    svg: iconShell('ContentStash icon option 8: Link Stack', `
  <rect x="14" y="14" width="100" height="100" rx="24" fill="${colors.cream}"/>
  <rect x="34" y="30" width="60" height="68" rx="14" fill="${colors.tealSoft}" stroke="${colors.teal}" stroke-width="5"/>
  <path d="M50 51H76" stroke="${colors.tealDark}" stroke-width="7" stroke-linecap="round"/>
  <path d="M50 68H68" stroke="${colors.tealDark}" stroke-width="7" stroke-linecap="round" opacity=".72"/>
  <path d="M45 90L59 76C64.523 70.477 73.477 70.477 79 76V76" stroke="${colors.coral}" stroke-width="10" stroke-linecap="round"/>
  <path d="M83 38L69 52C63.477 57.523 54.523 57.523 49 52V52" stroke="${colors.coral}" stroke-width="10" stroke-linecap="round"/>
`),
  },
  {
    id: '09-refined-cs',
    name: 'Refined CS',
    note: 'A grown-up monogram option, kept simple enough to read at popup size.',
    svg: iconShell('ContentStash icon option 9: Refined CS', `
  <rect x="14" y="14" width="100" height="100" rx="26" fill="${colors.teal}"/>
  <path d="M79 39C74.9 34.6 69.2 32 62.7 32C48.1 32 36 44.1 36 64C36 83.9 48.1 96 62.7 96C69.5 96 75.4 93.2 79.5 88.6" stroke="${colors.paper}" stroke-width="10" stroke-linecap="round"/>
  <path d="M57 64H76C83.18 64 89 69.82 89 77C89 84.18 83.18 90 76 90H55" stroke="${colors.cream}" stroke-width="10" stroke-linecap="round"/>
  <path d="M72 38H91" stroke="${colors.cream}" stroke-width="10" stroke-linecap="round"/>
  <path d="M75 51H91" stroke="${colors.cream}" stroke-width="10" stroke-linecap="round"/>
`),
  },
  {
    id: '10-compass-save',
    name: 'Compass Save',
    note: 'A distinct save/navigation hybrid: content selected, carried, and kept.',
    svg: iconShell('ContentStash icon option 10: Compass Save', `
  <rect x="14" y="14" width="100" height="100" rx="25" fill="${colors.teal}"/>
  <circle cx="64" cy="64" r="34" fill="${colors.paper}" opacity=".96"/>
  <path d="M75 32L68 59L95 53L73 72L80 99L61 77L34 84L56 65L49 38L68 59L75 32Z" fill="${colors.tealDark}"/>
  <circle cx="64" cy="64" r="8" fill="${colors.gold}" stroke="${colors.paper}" stroke-width="4"/>
`),
  },
];

function iconForPreview(option, x, y) {
  const body = option.svg
    .replace(/^<svg[^>]*>\s*<title[^>]*>.*?<\/title>/s, '')
    .replace(/<\/svg>\s*$/s, '')
    .trim();

  return `<g transform="translate(${x} ${y})">
    <rect width="196" height="254" rx="18" fill="#fffdf7" stroke="#ded3c2"/>
    <g transform="translate(34 24)">
      ${body}
    </g>
    <text x="98" y="184" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="16" font-weight="750" fill="${colors.ink}">${option.name}</text>
    <text x="98" y="210" text-anchor="middle" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="12" font-weight="700" fill="${colors.muted}">${option.id.slice(0, 2)}</text>
  </g>`;
}

mkdirSync(__dirname, { recursive: true });
mkdirSync(join(__dirname, 'svg'), { recursive: true });

for (const option of options) {
  writeFileSync(join(__dirname, 'svg', `${option.id}.svg`), option.svg);
}

const preview = `<svg width="1120" height="640" viewBox="0 0 1120 640" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="1120" height="640" fill="#f7f2e8"/>
  <text x="48" y="58" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="28" font-weight="800" fill="${colors.ink}">ContentStash Chrome Extension Icon Options</text>
  <text x="48" y="88" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif" font-size="15" font-weight="600" fill="${colors.muted}">SVG-first marks designed to stay legible at 16px and polished when enlarged in the popup.</text>
  ${options.map((option, index) => iconForPreview(option, 48 + (index % 5) * 212, 118 + Math.floor(index / 5) * 266)).join('\n  ')}
</svg>
`;

const readme = `# ContentStash Icon Options

Ten SVG-first replacement directions for the Chrome extension icon.

These avoid text-heavy marks so the toolbar icon remains readable at 16 px and the popup mark can be enlarged without pixelation.

## Options

${options.map((option) => `- ${option.id}: ${option.name}. ${option.note}`).join('\n')}

## Export note

Use the selected SVG as the source of truth, then export true PNG files at 16, 48, and 128 px for the Chrome extension manifest.
`;

writeFileSync(join(__dirname, 'icon-options-preview.svg'), preview);
writeFileSync(join(__dirname, 'README.md'), readme);

console.log(`Generated ${options.length} SVG options in ${join(__dirname, 'svg')}`);
console.log(`Generated preview: ${join(__dirname, 'icon-options-preview.svg')}`);
