## 2025-05-15 - [Accessible Input Foundation]
**Learning:** Foundational UI components like `Input` often miss basic accessibility links (label to input, error/helper text to input) which can be solved elegantly using React 18's `useId` hook.
**Action:** Always check if core UI components use `useId` for unique ID generation and correctly implement `aria-describedby` and `htmlFor` attributes to ensure a robust accessible foundation for all forms in the app.
