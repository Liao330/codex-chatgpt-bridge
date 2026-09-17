# Native Codex Browser Adapter

Preferred adapter sequence:

1. Use an already available Codex Browser or ChatGPT thread bridge.
2. Reuse the same user-controlled tab or thread identity when continuation is requested.
3. Verify mode, model, bound surface, and composer before prompting.
4. Send only after `run begin-submit`.
5. Confirm the observed acknowledgement immediately after Send.
6. Capture the complete response before closing or navigating the tab.
7. Preserve the private conversation identity in `private.json`, never in a public receipt.

Do not install a new browser backend merely to satisfy this contract. If no adapter provides all required capabilities, fail closed or use a manual handoff.
