# Deep Research Smoke: WCAG 2.2 keyboard-focus visibility

- Surface: visible ChatGPT web
- Mode: Deep Research
- Visible model label: Pro
- Submission count: 1
- Terminal result: complete
- Captured characters: 11226
- Response SHA-256: c853c8d96ffa23c6abb2cde7cc24915a525c170dfc08e9c4adc21b082a798d93
- Source restriction: current public W3C sources only
- Verification: decision-critical criterion levels and normative wording independently checked against W3C on 2026-08-30

WCAG 2.2 keyboard-focus visibility

Bottom line — [Inference]: For keyboard-focus visibility, WCAG 2.2 Level AA requires a visible focus indication, sufficient adjacent contrast for author-controlled visual focus information, and protection against the focused component being completely covered. Level AAA adds full non-obscuration and measurable minimum size/state-change contrast for the indicator. These focus-related criteria are necessary parts of their respective conformance levels, but they are not sufficient by themselves to establish whole-page WCAG conformance.
W3C
+3
W3C
+3
W3C
+3

[Public fact] The current published WCAG 2.2 is the W3C Recommendation dated 12 December 2024. The public errata page was last modified 28 August 2026. [Inference] I found no listed erratum changing the focus criteria discussed below as of 30 August 2026.
W3C
+1

1. Normative requirements versus explanatory guidance

[Public fact] Only the WCAG technical standard establishes normative requirements. Within that standard, the success-criterion wording and applicable normative definitions affect conformance; notes, diagrams and examples are informative. The separate Understanding documents, techniques and common-failure documents explain how W3C interprets or expects people to apply the criteria, but they do not create or alter requirements. A documented technique is not the only possible way to satisfy a criterion.
W3C
+1

Directly relevant criteria
Criterion	Level	Normative requirement, paraphrased	Role
1.4.11 Non-text Contrast	AA	Author-controlled visual information needed to identify a component or its focused state must contrast at least 3:1 with adjacent colours, subject to its user-agent exception.	Makes the visible indication distinguishable from its surroundings.
W3C
+1

2.4.7 Focus Visible	AA	A keyboard-operable interface must have a mode in which its keyboard-focus indicator is visible.	Requires the indication to exist and be visible.
W3C

2.4.11 Focus Not Obscured (Minimum)	AA	When a component receives keyboard focus, author-created content must not hide the component completely.	Prevents total coverage; partial coverage is permitted.
W3C

2.4.12 Focus Not Obscured (Enhanced)	AAA	No part of the keyboard-focused component may be hidden by author-created content.	Prohibits even partial coverage.
W3C

2.4.13 Focus Appearance	AAA	A visible focus indicator must contain an area at least equivalent to a two-CSS-pixel perimeter of the unfocused component and that area must change by at least 3:1 between focused and unfocused states. Two user-agent/default-indicator exceptions apply.	Quantifies indicator area and state-change contrast.
W3C

[Public fact] 2.4.11, 2.4.12 and 2.4.13 were added in WCAG 2.2. In the final Recommendation, Focus Appearance is Level AAA, not Level AA. Level AA conformance includes every Level A and AA criterion; Level AAA includes A, AA and AAA.
W3C
+1

2. Comparison

[Inference] A practical way to separate the requirements is:

Question being tested	Criterion	Test object	Threshold
Can the user see where keyboard focus is?	2.4.7 Focus Visible	Focus indicator	Visible in at least one keyboard-operating mode; no numeric area threshold in this SC.
Can the user see at least some of the focused control?	2.4.11 Focus Not Obscured (Minimum)	Focused component	It is not completely covered by author content.
Can the user see the whole focused control?	2.4.12 Focus Not Obscured (Enhanced)	Focused component	No part is covered by author content.
Is the focus indication visually substantial?	2.4.13 Focus Appearance	Changed indicator pixels	Two-pixel-perimeter-equivalent area and at least 3:1 focused-versus-unfocused change.
Does the indication stand out from nearby colours?	1.4.11 Non-text Contrast	Indicator versus adjacent colour	At least 3:1 adjacent contrast for applicable author-controlled visual information.

[Public fact] The two contrast tests are not interchangeable:

1.4.11 compares the focused indicator with colours immediately adjacent to it.

2.4.13 compares the same pixels between the focused and unfocused states.

An indicator can therefore satisfy one and fail the other. W3C provides examples of both combinations.
W3C

3. Clear pass and fail examples

These examples come from, or closely follow, W3C’s informative Understanding guidance; they illustrate application but do not add normative requirements.

Criterion	Clearly passes	Clearly fails
1.4.11	[Public fact] An author-styled focus outline has at least 3:1 contrast against every adjacent colour around the focused control.	[Public fact] A light-grey #AAA focus outline on white has about 2.3:1 adjacent contrast and is insufficient.
W3C

2.4.7	[Public fact] Tabbing to a button produces a visible border or other persistent visual change that identifies that button as focused.	[Public fact] CSS removes the browser outline and supplies no replacement focus indication. W3C lists this as a common failure.
W3C

2.4.11	[Public fact] A page has a sticky footer, but scroll padding moves each newly focused item so at least part of the item remains visible above the footer.	[Public fact] A sticky cookie banner completely covers a link after keyboard focus moves to that link.
W3C

2.4.12	[Public fact] Scroll padding ensures the entire focused control remains above a sticky footer, with no overlap.	[Public fact] The sticky footer covers even part of the focused control.
W3C

2.4.13	[Public fact] An author-provided solid two-CSS-pixel outline surrounds the component and its changed pixels have at least 3:1 contrast with those pixels in the unfocused state.	[Public fact] A combined two-pixel indicator has only a one-pixel portion that achieves the required contrast; the qualifying area is therefore too small.
W3C
+1
4. Ambiguities and interpretation limits

[Public fact] 2.4.7 is qualitative. Its normative text does not specify indicator thickness, area, shape or a focused-versus-unfocused contrast ratio. Those measurable requirements appear in 2.4.13, while adjacent contrast is addressed separately by 1.4.11.
W3C
+1

[Public fact] 2.4.11 contains no numerical minimum for how much of a component must remain visible. Partial obstruction is allowed at AA. [Inference] Consequently, an almost entirely covered control may meet the literal minimum while remaining difficult to use; W3C’s guidance recommends reducing the degree and frequency of partial obstruction.
W3C

[Public fact] The non-obscuration criteria principally evaluate the component, not an external focus ring. An external ring can be covered while the component itself remains visible. That situation may pass 2.4.11 or 2.4.12 but still fail 2.4.7. An indicator inside the component, or a visual change to the component itself, is treated differently.
W3C
+1

[Public fact] W3C’s note for 2.4.11 treats some user-opened persistent content differently. Its informative interpretation permits the user to reveal the focused component without advancing focus—for example by pressing Escape or scrolling. This note is official guidance, but notes remain non-normative under WCAG section 5.1.
W3C
+1

[Public fact] Focus Appearance has user-agent exceptions. It need not be assessed when the indicator cannot be author-adjusted, or when neither the default indicator nor its background has been modified. Changing the pixels behind a browser-default indicator can remove the second exception. [Inference] Therefore, merely relying on a browser default can satisfy the exception without guaranteeing equally prominent indicators in every browser and operating system.
W3C

[Inference] Complex widgets require human judgment. For tab lists, grids, rating controls and other composite widgets, an evaluator must determine whether users perceive the whole widget or a subcomponent as the relevant control. W3C supplies examples, but there is no universal CSS selector or automated rule that makes this perceptual determination.
W3C

[Unverified] No particular website or component library was tested for this report. Whether any implementation conforms to WCAG 2.2—or satisfies legislation, regulation, procurement rules or contractual obligations—has not been established.

5. Implementation checklist

[Inference] Criteria-oriented checklist derived from the normative text and W3C guidance:

Level AA focus baseline

 Keyboard-test every link, button, input, menu item and custom widget using forward and reverse navigation.

 Ensure every keyboard-operable component has an identifiable visual focused state.

 Do not use outline: none or equivalent removal unless a visible replacement is provided.

 Keep the indication visible for as long as the component retains keyboard focus.

 For author-styled indicators, measure at least 3:1 contrast against every adjacent colour, including gradients, images and component interiors.

 Test sticky headers, sticky footers, cookie notices, drawers, chat windows, notifications and non-modal overlays.

 Ensure none of those author-created layers can completely cover the currently focused component.

 Ensure modal dialogs receive focus and constrain focus appropriately rather than leaving keyboard focus hidden behind the dialog.

 Repeat testing in responsive layouts, scrollable regions, expanded menus, validation states and other automatically presented page variations.

 Test components after changing their background or border; those changes can weaken a browser-default indicator or remove a user-agent exception.

Level AAA enhancements

 Ensure no author-created content covers any portion of the focused component.

 For every non-exempt indicator, calculate or conservatively exceed the area of a two-CSS-pixel perimeter.

 Confirm that the qualifying indicator pixels change by at least 3:1 between focused and unfocused states.

 Separately confirm 1.4.11 adjacent contrast; passing the state-change test does not prove adjacent contrast.

 Identify the appropriate component or subcomponent for composite widgets and document the testing decision.

 Prefer a simple, solid indicator larger than the minimum where area calculations would otherwise be complex.

 Record screenshots and measured colour pairs for focused, unfocused and overlay-obscured states.

Exact W3C sources

All URLs were accessed 2026-08-30.

Normative technical standard
https://www.w3.org/TR/WCAG22/
https://www.w3.org/TR/WCAG22/#non-text-contrast
https://www.w3.org/TR/WCAG22/#focus-visible
https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum
https://www.w3.org/TR/WCAG22/#focus-not-obscured-enhanced
https://www.w3.org/TR/WCAG22/#focus-appearance
https://www.w3.org/TR/WCAG22/#interpreting-normative-requirements
https://www.w3.org/TR/WCAG22/#conformance-level
Informative W3C guidance
https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html
https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html
https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html
https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-enhanced.html
https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
https://www.w3.org/WAI/standards-guidelines/wcag/docs/
Current errata
https://www.w3.org/WAI/WCAG22/errata/
