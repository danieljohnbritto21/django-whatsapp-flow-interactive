# TODO

- [x] Fix WhatsApp interactive list payload causing Meta Graph API `400 Bad Request` when sending packages selection.
- [x] Inspect and update `send_interactive_list()` in `whatsapp_app/whatsapp_service.py` to strictly comply with WhatsApp Cloud API limits (title/description lengths, section/row limits, safe defaults).
- [x] Update `send_packages_interactive_selection()` row text to match constraints (or rely on centralized truncation).
- [x] Run `python -m py_compile` to ensure no syntax errors.


