from tests.conftest import AUTH


async def test_register_repo_returns_it(client):
    resp = await client.post(
        "/api/v1/repos",
        json={"slug": "racing-platform", "name": "Racing Platform", "path": "/Users/tom/Projects/racing-platform"},
        headers=AUTH,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["slug"] == "racing-platform"
    assert body["id"] > 0


async def test_register_repo_requires_token(client):
    resp = await client.post("/api/v1/repos", json={"slug": "x", "name": "x", "path": "/x"})
    assert resp.status_code == 401
