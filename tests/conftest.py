import os

# Ensure offscreen and software rendering in headless/sandbox test runs
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QSG_RHI_BACKEND"] = "software"
os.environ["QT_QUICK_BACKEND"] = "software"

