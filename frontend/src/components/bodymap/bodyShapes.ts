import type { BodyRegion, BodyView } from "../../utils/bodyMap";

/**
 * Body outline on a 240-wide canvas, centred on x = 120. Paired limbs are drawn once for the viewer's left
 * and mirrored. Neighbouring regions share exact edge coordinates so the figure has no gaps between parts.
 */
export const FIGURE_WIDTH = 240;
export const FIGURE_VIEWBOX = "0 -30 240 564";
export const MIRROR = `matrix(-1 0 0 1 ${FIGURE_WIDTH} 0)`;

export type RegionShape = { d: string; mirror?: boolean };
export type RegionLayer = { region: BodyRegion; shapes: RegionShape[] };

const NECK = "M111 58 C112 70 111 78 106 88 C114 92 126 92 134 88 C129 78 128 70 129 58 Z";
const HEAD = "M120 13 C133 13 142 23 142 38 C142 52 136 63 127 67 C123 69 117 69 113 67 C104 63 98 52 98 38 C98 23 107 13 120 13 Z";
const EAR = "M100.5 33 C95.5 31 93.5 36 94.5 42 C95.5 48 98.5 50 101.5 48.5 Z";
const SHOULDER = "M90 93 C80 95 72 99 68 106 C64 113 63 122 64 132 L80 134 C82 126 84 120 88 116 C88 108 89 101 90 93 Z";
const UPPER_ARM = "M64 132 L80 134 C79 152 78 172 77 196 L59 194 C59 172 61 152 64 132 Z";
const ELBOW = "M59 194 L77 196 C77 204 76 212 75 220 L57 218 C57 210 58 202 59 194 Z";
const FOREARM = "M57 218 L75 220 C74 240 72 258 70 276 L58 276 C56 258 56 238 57 218 Z";
const HAND =
  "M58 276 L70 276 C71.5 282 73 288 73 296 L73 309 Q71.3 313.5 69.5 309 L69.5 300.5 L69.5 314 Q67.5 319 65.5 314 L65.5 301 " +
  "L65.5 316 Q63.5 321 61.5 316 L61.5 301 L61.5 313.5 Q59.5 318.5 57.5 313.5 L57.5 300 C55.5 302 52.5 304 50.5 301.5 " +
  "C49 299 51 295 53.5 291 C55.5 287 56.5 281 58 276 Z";
const HIP = "M87 232 L153 232 C155 242 156 254 155 268 C146 276 132 280 120 276 C108 280 94 276 85 268 C84 254 85 242 87 232 Z";
const THIGH = "M85 268 C94 276 108 280 120 276 C117 290 115 310 113 330 C112 344 112 354 112 364 L88 364 C87 350 86 336 85 320 C83 302 83 284 85 268 Z";
const KNEE = "M88 364 L112 364 C113 374 113 384 112 394 L89 394 C88 384 87 374 88 364 Z";
const LOWER_LEG = "M89 394 L112 394 C114 410 113 428 110 446 C109 458 108 468 107 478 L95 478 C94 468 92 456 90 444 C87 428 87 410 89 394 Z";
const FOOT_FRONT = "M95 478 L107 478 C107.5 486 109 492 111 498 C113 503 112 508 107 508 L88 508 C83 508 82 504 85 500 C89 494 93 487 95 478 Z";
const FOOT_BACK = "M95 478 L107 478 C108 488 109 497 108 504 C107 508 104 509 100 509 L90 509 C86 509 85 506 88 503 C91 499 93 490 95 478 Z";

const CHEST =
  "M106 88 C114 92 126 92 134 88 C140 90 145 91 150 93 C151 101 152 108 152 116 L152 128 C151 139 150 150 150 160 " +
  "L90 160 C90 150 89 139 88 128 L88 116 C88 108 89 101 90 93 C95 91 100 90 106 88 Z";
const ABDOMEN = "M90 160 L150 160 C150 176 149 190 148 202 C149 214 151 224 153 232 L87 232 C89 224 91 214 92 202 C91 190 90 176 90 160 Z";
const UPPER_BACK =
  "M106 88 C114 92 126 92 134 88 C140 90 145 91 150 93 C151 101 152 108 152 116 L152 128 C151 144 150 160 149.6 176 " +
  "L90.4 176 C90 160 89 144 88 128 L88 116 C88 108 89 101 90 93 C95 91 100 90 106 88 Z";
const LOWER_BACK = "M90.4 176 L149.6 176 C149.2 186 148.6 194 148 202 C149 214 151 224 153 232 L87 232 C89 224 91 214 92 202 C91.4 194 90.8 186 90.4 176 Z";

function limbs(foot: string): RegionLayer[] {
  return [
    { region: "shoulder", shapes: [{ d: SHOULDER, mirror: true }] },
    { region: "arm", shapes: [{ d: UPPER_ARM, mirror: true }, { d: FOREARM, mirror: true }] },
    { region: "elbow", shapes: [{ d: ELBOW, mirror: true }] },
    { region: "wrist_hand", shapes: [{ d: HAND, mirror: true }] },
    { region: "thigh", shapes: [{ d: THIGH, mirror: true }] },
    { region: "knee", shapes: [{ d: KNEE, mirror: true }] },
    { region: "lower_leg", shapes: [{ d: LOWER_LEG, mirror: true }] },
    { region: "ankle_foot", shapes: [{ d: foot, mirror: true }] },
  ];
}

/** Paint order matters: the head is drawn after the neck so the neck tucks under the jaw. */
export const REGION_LAYERS: Record<BodyView, RegionLayer[]> = {
  front: [
    { region: "neck", shapes: [{ d: NECK }] },
    { region: "head", shapes: [{ d: EAR, mirror: true }, { d: HEAD }] },
    { region: "chest", shapes: [{ d: CHEST }] },
    { region: "abdomen", shapes: [{ d: ABDOMEN }] },
    { region: "hip", shapes: [{ d: HIP }] },
    ...limbs(FOOT_FRONT),
  ],
  back: [
    { region: "neck", shapes: [{ d: NECK }] },
    { region: "head", shapes: [{ d: EAR, mirror: true }, { d: HEAD }] },
    { region: "upper_back", shapes: [{ d: UPPER_BACK }] },
    { region: "lower_back", shapes: [{ d: LOWER_BACK }] },
    { region: "hip", shapes: [{ d: HIP }] },
    ...limbs(FOOT_BACK),
  ],
};

/** Non-interactive anatomical detail lines, drawn on top of the regions. */
export const DETAIL_LINES: Record<BodyView, string[]> = {
  front: [
    "M108.5 38 Q112 35.5 115.5 38 M124.5 38 Q128 35.5 131.5 38",
    "M120 41 L118.4 50 L121.2 51",
    "M115 57.5 Q120 60.5 125 57.5",
    "M107 97 Q113 100.5 119 98 M121 98 Q127 100.5 133 97",
    "M95 137 Q106 148 118 141 M122 141 Q134 148 145 137",
    "M120 166 L120 194",
    "M97 246 Q106 261 116 271 M143 246 Q134 261 124 271",
    "M94 377 Q100 371 106 377 M134 377 Q140 371 146 377",
    "M89 503 L89 507.5 M92.5 502 L92.5 507.5 M151 503 L151 507.5 M147.5 502 L147.5 507.5",
  ],
  back: [
    "M103 24 C112 18 128 18 137 24",
    "M101 54 Q120 61 139 54",
    "M120 94 L120 226",
    "M99 106 C101 119 103 129 108 138 M141 106 C139 119 137 129 132 138",
    "M64 207 Q68 210 72 207 M168 207 Q172 210 176 207",
    "M120 242 L120 270 M92 266 Q104 275 117 272 M148 266 Q136 275 123 272",
    "M92 380 Q100 385 108 380 M132 380 Q140 385 148 380",
    "M99 402 Q97 421 100 440 M141 402 Q143 421 140 440",
  ],
};

export const DETAIL_DOTS: Record<BodyView, { cx: number; cy: number }[]> = {
  front: [{ cx: 120, cy: 202 }],
  back: [
    { cx: 110, cy: 224 },
    { cx: 130, cy: 224 },
  ],
};
