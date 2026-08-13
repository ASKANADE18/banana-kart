from app.models.product import Product

def test_get_product_image_returns_presigned_url(
    client,
    db_session,
    monkeypatch,
):
    product = Product(
        name="Banana",
        price_cents=50,
        stock_quantity=100,
        image_key="products/1/banana.jpg",
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    def fake_presigned_url(image_key: str):
        assert image_key == "products/1/banana.jpg"
        return "https://example.com/fake-presigned-url"

    monkeypatch.setattr(
        "app.api.routes.products.generate_product_image_url",
        fake_presigned_url,
    )

    response = client.get(
        f"/products/{product.id}/image"
    )

    assert response.status_code == 200
    assert response.json() == {
        "image_url": "https://example.com/fake-presigned-url"
    }

def test_get_product_image_returns_404_when_no_image(
    client,
    db_session,
):
    product = Product(
        name="Banana",
        price_cents=50,
        stock_quantity=100,
        image_key=None,
    )

    db_session.add(product)
    db_session.commit()
    db_session.refresh(product)

    response = client.get(
        f"/products/{product.id}/image"
    )

    assert response.status_code == 404