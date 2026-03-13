Fix venv path:
venv\Scripts\python -m ensurepip --upgrade
venv\Scripts\python -m pip install --upgrade pip

Docling and Transformer versions mismatch:
pip uninstall transformers -y
pip uninstall docling -y
pip install docling