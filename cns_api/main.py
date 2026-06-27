"""CNS API service entry point."""
import uvicorn
from cns_api.app import create_app
from cns_api.config import get_api_host, get_api_port

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "cns_api.main:app",
        host=get_api_host(),
        port=get_api_port(),
        reload=False,
    )
