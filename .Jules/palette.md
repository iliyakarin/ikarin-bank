## 2025-05-22 - [Enhancing Core Component Accessibility]
**Learning:** Generic form components often lack proper label-input association and ARIA descriptions for helper/error text, which significantly impacts screen reader usability. Using React 18's `useId` hook is the most robust way to ensure unique, stable IDs for these associations.
**Action:** Always implement `useId` in reusable form components (Inputs, Selects, etc.) to link labels (`htmlFor`) and descriptive text (`aria-describedby`).
