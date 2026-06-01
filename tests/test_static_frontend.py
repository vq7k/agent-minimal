import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from server import create_app


def test_serves_frontend_index_when_dist_exists(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text('<div id="root">agent ui</div>', encoding="utf-8")

    client = TestClient(create_app(frontend_dist=frontend_dist))

    response = client.get("/")

    assert response.status_code == 200
    assert "agent ui" in response.text
    assert response.headers["content-type"].startswith("text/html")


def test_spa_fallback_keeps_api_routes_available(tmp_path: Path) -> None:
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text('<div id="root">agent ui</div>', encoding="utf-8")

    client = TestClient(create_app(frontend_dist=frontend_dist))

    agents_response = client.get("/agents")
    fallback_response = client.get("/chat/alpha")

    assert agents_response.status_code == 200
    assert agents_response.json() == {"agents": ["alpha", "bravo", "charlie", "delta"]}
    assert fallback_response.status_code == 200
    assert "agent ui" in fallback_response.text
