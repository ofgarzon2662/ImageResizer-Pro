def test_create_upload_returns_presigned_contract_shape(client):
    response = client.post(
        "/v1/uploads",
        json={
            "filename": "photo.png",
            "contentType": "image/png",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert "uploadUrl" in payload
    assert "inputKey" in payload
    assert "expiresInSeconds" in payload
    assert payload["inputKey"].startswith("uploads/")
