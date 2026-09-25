# Gui architecture

PySide6 desktop under presentation/desktop (app, windows, views, viewmodels, widgets, dialogs, resources). Must not parse, access ChromaDB, call Gemini, retrieve or evaluate; calls application use cases. Only an app.py scaffold exists (PySide6 imported lazily).
