## 2025-05-15 - [Accessible Form Inputs]
**Learning:** Shared UI components often miss fundamental accessibility links (label -> input) which can be fixed globally using `React.useId()`.
**Action:** Always ensure `id`, `htmlFor`, and `aria-describedby` are properly linked in reusable form components to improve screen reader support.
