## 2025-05-14 - Icon-only Button Accessibility and Feedback
**Learning:** Icon-only buttons (like refresh or navigation icons) are common in modern glassmorphism designs but often lack proper accessibility labels for screen readers. Furthermore, providing immediate visual feedback (like a spinning animation) during asynchronous background refreshes significantly improves the perceived responsiveness of the application.
**Action:** Always include `aria-label` on icon-only buttons and use `animate` properties (e.g., from Framer Motion) to indicate loading states even when the main UI isn't blocked by a full-page loader.
## 2025-05-15 - [Accessible Input Foundation]
**Learning:** Foundational UI components like `Input` often miss basic accessibility links (label to input, error/helper text to input) which can be solved elegantly using React 18's `useId` hook.
**Action:** Always check if core UI components use `useId` for unique ID generation and correctly implement `aria-describedby` and `htmlFor` attributes to ensure a robust accessible foundation for all forms in the app.
## 2025-05-22 - [Pattern] Missing aria-labels on icon-only buttons
**Learning:** The application uses several icon-only buttons (Refresh, Navigation, Eye toggle) that either completely lack `aria-label` or rely only on `title`. While `title` can provide some context, `aria-label` is more reliable for screen readers and consistent with accessible design patterns.
**Action:** Always check icon-only components for `aria-label` and add them using a descriptive name (e.g., `item.name` for nav links).
