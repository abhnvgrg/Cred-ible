# Design System Document: The Luminal Logic Framework

## 1. Overview & Creative North Star: "The Digital Alchemist"
This design system is built to move beyond the cold, utilitarian nature of traditional fintech. Our Creative North Star is **"The Digital Alchemist"**—a philosophy that blends the high-stakes precision of AI credit scoring with a premium, tactile editorial experience. 

We reject the "Bootstrap" look of flat boxes and rigid lines. Instead, we embrace **Intentional Asymmetry** and **Tonal Depth**. By using overlapping glass layers, oversized typography, and deep-space gradients, we create a sense of "prestige intelligence." The UI shouldn't just show data; it should feel like a high-end physical dashboard carved from obsidian and light.

---

## 2. Colors & Surface Philosophy
The palette is rooted in a "Deep Dark" foundation, using the `surface` and `surface-container` tiers to create a sense of infinite depth.

### The "No-Line" Rule
**Borders are a failure of hierarchy.** In this system, 1px solid borders for sectioning are strictly prohibited. Boundaries must be defined solely through:
1.  **Background Color Shifts:** Placing a `surface-container-high` card against a `surface-container-low` background.
2.  **Tonal Transitions:** Soft, internal glows that define an edge without a stroke.

### Surface Hierarchy & Nesting
Treat the UI as physical layers of frosted glass.
*   **Base Level:** `surface` (#0a0e19) — The infinite void.
*   **Sectioning:** `surface-container-low` (#0f131f) — Broad content areas.
*   **Interaction/Focus:** `surface-container-highest` (#202535) — Elevated interactive elements.

### The "Glass & Gradient" Rule
To achieve the signature "Stripe-meets-CRED" look, use **Glassmorphism** for floating elements. Use semi-transparent `surface-variant` colors with a `backdrop-filter: blur(20px)`. 
*   **Signature Textures:** Main CTAs must use a linear gradient from `primary` (#a3a6ff) to `secondary` (#c180ff) at a 135° angle. This adds "soul" and a sense of energy to the platform’s decision-making engine.

---

## 3. Typography: Editorial Authority
We utilize two distinct voices: **Plus Jakarta Sans** for character and **Inter** for utility.

*   **Display & Headlines (Plus Jakarta Sans):** These are your "Editorial" voices. Use `display-lg` (3.5rem) with tight letter-spacing (-0.04em) to create high-impact hero moments. This conveys authority and modernism.
*   **Title & Body (Inter):** The "Functional" voice. Inter’s neutral, high-legibility architecture ensures that complex financial data remains readable. 
*   **Hierarchy Tip:** Never settle for uniform sizing. Create drama by pairing a `display-sm` headline with a `label-sm` caption in `on-surface-variant`. The contrast in scale creates a premium, "designed" feel.

---

## 4. Elevation & Depth: Tonal Layering
Traditional shadows are often too heavy for dark mode. We use **Ambient Illumination.**

*   **The Layering Principle:** Stack `surface-container-lowest` (#000000) cards on `surface-container-low` backgrounds to create a "recessed" look, or `surface-container-high` on `surface` for a "lifted" look.
*   **Ambient Shadows:** For floating modals, use a blur radius of 40px-60px with a 4% opacity shadow tinted with `surface-tint` (#a3a6ff). This mimics a soft blue glow rather than a black smudge.
*   **The "Ghost Border" Fallback:** If a container needs more definition (e.g., in high-density data views), use a **Ghost Border**: `outline-variant` (#444855) at 15% opacity.
*   **Gradient Borders:** For primary cards (like "Your Credit Score"), use a 1.5px border with a gradient stroke from `primary` to `secondary`. This should be the *only* place a stroke is used.

---

## 5. Components & Primitives

### Buttons
*   **Primary:** Gradient fill (`primary` to `secondary`), white text, `xl` (1.5rem) rounded corners. Add a subtle `primary-dim` outer glow on hover.
*   **Secondary:** Glass-morphic. `surface-variant` at 20% opacity with a heavy backdrop blur and a "Ghost Border."
*   **Tertiary:** No background. `on-surface-variant` text. High-contrast hover state using `on-surface`.

### Input Fields
*   **Style:** Deep recessed look. Use `surface-container-lowest` as the fill. 
*   **State:** On focus, the "Ghost Border" transitions to a 1px `primary` border with a soft `primary_dim` outer glow. Labels should use `label-md` and be positioned with generous padding.

### Cards (The Data Vessel)
*   **Rule:** Forbid divider lines. 
*   **Separation:** Use vertical white space (32px or 48px) and background shifts. If you must separate two items in a list, use a subtle shift from `surface-container` to `surface-container-low`.
*   **Corner Radius:** Use the `xl` (1.5rem) token for main containers to keep the "CRED" aesthetic soft and approachable.

### The "Credit Pulse" (Specialty Component)
*   A circular data visualization component. Use a `secondary_fixed` glow to represent the "AI Scanning" state. The stroke should utilize the `tertiary` (Vibrant Green) for high scores and `error` (Red/Orange) for risk.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use extreme white space. Let the background color "breathe" around your cards.
*   **Do** use `on-surface-variant` (#a7aaba) for secondary text to maintain a sophisticated low-contrast look.
*   **Do** apply `backdrop-filter: blur` to any element overlapping a gradient background.

### Don’t:
*   **Don’t** use pure white (#FFFFFF) for text. Use `on-surface` (#e8eafb) to prevent eye strain.
*   **Don’t** use 100% opaque borders. They break the "Liquid UI" illusion.
*   **Don’t** use standard "drop shadows." If it doesn't look like a soft glow of light, it doesn't belong.
*   **Don’t** crowd the interface. If a screen feels busy, increase the spacing between containers by 2x.

### Accessibility Note:
While we use low-contrast neutrals for elegance, all actionable text and data points (Credit Scores, Interest Rates) must maintain a minimum contrast ratio of 4.5:1 against their respective surface containers. Use `primary-fixed` and `tertiary-fixed` for critical data highlights.