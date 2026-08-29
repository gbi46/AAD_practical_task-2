python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest test_mcp_server.py -v
npm run inspector