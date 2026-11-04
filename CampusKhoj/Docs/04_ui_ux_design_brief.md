<!-- File: 04_ui_ux_design_brief.md -->
# CampusKhoj — UI/UX Design Brief

Version 1.0 · 1 November 2026 · AI-generated for the project team

## 1. Product & Design Vision

CampusKhoj should feel like a **well-kept campus notice board that came to life**: warm paper tones, confident green, a spark of saffron. It must look hand-made for a college, not like a generic template. We deliberately avoid the "AI product" look: no purple/blue gradient hero, no glassmorphism, no neon glow, no floating gradient blobs, no robot/sparkle iconography.

**Brand personality:** trustworthy, helpful, a little warm, quietly confident. Name meaning: *Khoj* = search/find.

Two websites, one family:
- **Student Portal** — light, warm, friendly.
- **Admin Portal** — dark charcoal, denser, data-forward, same accents so it clearly belongs to the same product.

## 2. Target Users & Context of Use

| Persona | Context |
|---|---|
| Student (Kondhwa / Bibwewadi) | Phone, one hand, between lectures, campus Wi-Fi/mobile data; wants to finish in seconds |
| Security staff | Desk PC, interrupted often, needs quick lookups and big tap targets |
| Campus admin / super admin | Laptop, reviewing tables, exporting CSVs |

Devices: mobile-first for students (360–430 px), desktop-first for admin (≥ 1280 px) but usable on tablet.

## 3. Design Goals & Principles

1. **Clarity over cleverness** — one primary action per screen.
2. **Campus always visible** — a campus chip (Kondhwa / Bibwewadi) is on every student screen so no one posts in the wrong place.
3. **Show progress, not mystery** — the timeline is a first-class component.
4. **Motion with meaning** — animation explains change (new event, tab switch, saved), never decorates endlessly.
5. **Private stays private** — UI clearly separates public details from private verification details.
6. **Mobile-first, thumb-friendly** — bottom nav on student mobile.
7. **Accessible by default** — contrast, labels, keyboard, reduced motion.
8. **Forgiving forms** — inline validation, drafts preserved on error.

## 4. Information Architecture

### Student Portal
| Page | Purpose |
|---|---|
| `/login` | PRN + password |
| `/change-password` | Forced on first login; only reachable page until done |
| `/profile-setup` | Name, phone, optional email (once) |
| `/home` | Greeting, campus chip, quick actions, recent items in own campus, mini stats |
| `/campus/kondhwa`, `/campus/bibwewadi` | Two sections: tabs **Lost** / **Found**, search + filters, cards |
| `/item/lost/:id`, `/item/found/:id` | Detail + timeline + claim/matches |
| `/report-lost` | Lost complaint form (own campus only) |
| `/report-found` | Found report form (own campus only) |
| `/my-reports` | My lost/found reports with status chips |
| `/my-claims` | Claims, verification questions, timeline |
| `/notifications` | Read/unread list |
| `/account` | Change password, profile |

Navigation: mobile bottom bar (Home · Campuses · **＋ Report** · Claims · Alerts); desktop top bar with the same items. Campus switch is a segmented control (Kondhwa | Bibwewadi); the student's own campus is marked "Your campus" and the other is labelled "Browse only".

### Admin Portal
| Page | Purpose |
|---|---|
| `/login` | Staff username + password |
| `/dashboard` | KPI cards, charts, pending claims |
| `/items` | All items table (campus, type, status, category, date filters; CSV export) |
| `/items/:type/:id` | Full detail incl. private fields, timeline, matches |
| `/claims`, `/claims/:id` | Queue, review, verification, approve/reject, handover |
| `/users` | Students, PRN registry, import, suspend, reset |
| `/staff` | Staff accounts (super admin) |
| `/analytics` | Campus comparison, trends |
| `/audit` | Audit log viewer |

Navigation: fixed left sidebar, top bar with campus filter (All / Kondhwa / Bibwewadi — locked for campus admins).

## 5. Key Screens & Wireframe Descriptions

**5.1 Student Login** — Centered card on cream background with a subtle paper grain. Heading "Welcome to CampusKhoj". Fields: PRN (numeric keypad on mobile), Password (show/hide). Helper line: "First time? Your PRN is your password — you'll change it next." Primary button (saffron, ink text). Entry animation: card rises 12 px and fades in.

**5.2 Change Password (forced)** — Same card layout, no nav. Shows 3 live rules with ticks that animate when satisfied: ≥ 8 characters · not your PRN · not common. Strength bar fills smoothly. Button disabled until valid. Success: green check draws itself, then redirect.

**5.3 Home** — Top: "Hi, {name}" + campus chip. Two big action tiles: **I lost something** (clay/terracotta accent) and **I found something** (green accent). Below: "Latest in {campus}" horizontal card strip; stats row (animated counters).

**5.4 Campus Section** — Segmented control Kondhwa | Bibwewadi with sliding underline. Under it: search bar, filter chips (Category, Location, Colour, Date), sub-tabs Lost | Found. Result cards in a responsive grid: image (or category icon), item name, location, date, status chip, "Lost"/"Found" ribbon. Cards stagger in (40 ms apart). Empty state: illustrated empty notice board with "Nothing here yet — be the first to post."

**5.5 Item Detail** — Left/top: large image, public details. Right/below: **Timeline** (vertical stepper) and action panel. Lost owner sees "Possible matches" with score bars; others see "Claim this item" (found only, own campus). Private details are never shown here.

**5.6 Report Lost / Found** — Single column, 6 essential fields visible: Item name, Category (icon chips), Location (campus-filtered), Date/time, Colour, Description; optional "More details" accordion (brand, image). Found form adds custody toggle and "Private identifying detail (only staff will see this)" with a lock icon. Submit shows a progress ring then success sheet with the new timeline.

**5.7 My Claims** — List of claims with status chips; opening one shows its own timeline and any verification questions with answer boxes.

**5.8 Admin Dashboard** — Dark canvas. Row of 6 KPI cards (Lost, Found, Pending claims, Returned, Recovery rate, Active students) with count-up. Two charts: monthly trend (line) and top locations (bar), plus a campus comparison (Kondhwa vs Bibwewadi). Right rail: "Needs attention" list (pending claims older than 24 h).

**5.9 Admin Items Table** — Sticky filter bar; zebra-free dense rows; status chips; row hover highlight; slide-over drawer for quick view; "Export CSV" button.

**5.10 Admin Claim Review** — Three columns: claimant info (PRN, campus), item public + private details, verification panel (add question, answer, VERIFIED/FAILED toggle). Bottom sticky bar: Reject · Request more info · Approve. Handover step appears as a distinct panel after approval.

## 6. Interactions & Micro-Interactions

| Moment | Behaviour |
|---|---|
| Form validation | Inline, on blur; error text slides down 150 ms; field border turns clay |
| Loading | Skeleton cards (soft shimmer), not spinners, for lists; ring for submits |
| Empty states | Friendly illustration + one action |
| Errors | Toast top-right (admin) / top-center (student), 4 s, dismissible |
| Success | Toast + checkmark draw; confetti is **not** used (keeps tone calm) |
| Timeline | Line grows downward; each node pops (scale 0.6→1) as it enters; latest node pulses gently once |
| Tabs / segmented control | Underline slides to selection (250 ms) |
| Cards | Hover lift 4 px + shadow; press scale 0.98 |
| Counters | Count-up 600 ms on first view only |
| Page transitions | 200 ms fade/slide; none when reduced motion is on |
| Notification bell | Badge pops when count increases |

**Motion budget:** ≤ 400 ms for UI transitions, ≤ 800 ms for one-off celebratory moments, never looping except the single "current step" pulse (stops after 3 cycles). Respect `prefers-reduced-motion: reduce` by replacing movement with instant state change.

## 7. Visual Design Direction

**Palette (design tokens)**

| Token | Student Portal | Admin Portal | Use |
|---|---|---|---|
| `--bg` | `#FAF6EE` cream | `#1E2420` charcoal | Page background |
| `--surface` | `#FFFFFF` | `#28302B` | Cards |
| `--primary` | `#1F4D3A` forest green | `#3E8E6A` lifted green | Headings, links, "Found" |
| `--accent` | `#E8892B` saffron | `#E8892B` saffron | Primary buttons, highlights |
| `--lost` | `#B8532F` terracotta | `#D9714C` | "Lost" ribbons/tiles |
| `--sage` | `#DCE8DF` | `#33403A` | Subtle fills, chips |
| `--text` | `#2B2B2B` | `#F2EEE4` | Body |
| `--muted` | `#6B6B63` | `#A9AFA6` | Secondary text |
| Semantic | success `#2F7D4F`, warning `#C98A00`, danger `#B3261E`, info `#2C6E8F` | adjusted for dark | Status |

**Contrast rule:** buttons on saffron use **ink text (`#2B2B2B`)**, not white (white on `#E8892B` fails AA). Verify all pairs with a contrast checker before handoff.

**Typography:** headings **Fraunces** (soft serif, 600), body **DM Sans** (400/500/700). Fallbacks: Georgia / system-ui. Self-host fonts. Scale: 12 / 14 / 16 / 20 / 24 / 32 / 40 px; body 16 px, line-height 1.5.

**Iconography & imagery:** simple 1.75 px outline icons (Lucide-style), rounded caps; category icons (calculator, wallet, key, bag, book, ID card, earphones). Illustrations: flat, paper-cut style in the palette; no 3D, no gradients. Photos of items are the real content and get 12 px rounded corners.

**Layout & spacing:** 8 px grid; radii 12 px (cards), 999 px (chips); max content width 1120 px (student desktop), full-width with 240 px sidebar (admin). Paper grain: ≤ 3% opacity noise on the student background only.

## 8. Accessibility Requirements

- Target **WCAG 2.2 AA**.
- Text contrast ≥ 4.5:1 (3:1 large text and UI components); never rely on colour alone (status chips have text + icon).
- Full keyboard operation; visible 2 px focus ring in `--accent` with 2 px offset.
- Labels on every input; error text linked via `aria-describedby`; live regions for toasts.
- Timeline is an ordered list (`<ol>`) with time elements, readable by screen readers.
- Touch targets ≥ 44 × 44 px.
- Reduced-motion and 200% zoom supported.

## 9. Design Handoff & Assets

| Deliverable | Format |
|---|---|
| Design tokens | `tokens.css` (CSS variables) shared by both portals |
| Component library | Figma (or Penpot) file: buttons, inputs, chips, cards, timeline, table, toast, modal |
| Screen designs | Mobile + desktop frames for each page above |
| Icons/illustrations | SVG |
| Motion spec | Short table (duration/easing per interaction) + prototype clips |

Process: designer shares tokens first (Sprint 1) → devs build `tokens.css` and base components → weekly design review of built pages vs Figma → version Figma pages as `v1.0`, `v1.1`.
