"""
Contract tests for Recipe Explorer API endpoints.
Verifies response structure, HTTP status codes, and error handling.
"""
import json
from io import BytesIO
from pathlib import Path

import pytest

from scripts.validate_schema import validate_recipe_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestHealthAndPages:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_home_page_loads(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "Recipe Explorer" in response.text

    def test_recipe_pages_load(self, client, clean_storage, sample_recipe_data):
        create_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = create_response.json()["id"]

        assert client.get(f"/recipes/{recipe_id}").status_code == 200
        assert client.get("/recipes/new").status_code == 200
        assert client.get(f"/recipes/{recipe_id}/edit").status_code == 200
        assert client.get("/import").status_code == 200

    def test_recipe_detail_not_found(self, client, clean_storage):
        response = client.get("/recipes/missing-recipe")
        assert response.status_code == 404


class TestRecipeListAndSearch:
    def test_get_all_recipes(self, client, clean_storage):
        response = client.get("/api/recipes")
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert isinstance(data["recipes"], list)

    def test_search_recipes(self, client, clean_storage, sample_recipe_data):
        client.post("/api/recipes", json=sample_recipe_data)
        client.post(
            "/api/recipes",
            json={**sample_recipe_data, "title": "Chocolate Cake"},
        )

        response = client.get("/api/recipes", params={"search": "chocolate"})
        assert response.status_code == 200
        recipes = response.json()["recipes"]
        assert len(recipes) == 1
        assert recipes[0]["title"] == "Chocolate Cake"


class TestRecipeCrud:
    def test_create_and_get_recipe(self, client, clean_storage, sample_recipe_data):
        create_response = client.post("/api/recipes", json=sample_recipe_data)
        assert create_response.status_code == 201

        recipe = create_response.json()
        assert "id" in recipe
        assert recipe["title"] == sample_recipe_data["title"]

        get_response = client.get(f"/api/recipes/{recipe['id']}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == recipe["id"]

    def test_get_recipe_not_found(self, client, clean_storage):
        response = client.get("/api/recipes/non-existent-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"

    def test_update_recipe(self, client, clean_storage, sample_recipe_data):
        create_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = create_response.json()["id"]

        update_payload = {**sample_recipe_data, "title": "Updated Recipe"}
        response = client.put(f"/api/recipes/{recipe_id}", json=update_payload)
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Recipe"

    def test_update_recipe_not_found(self, client, clean_storage, sample_recipe_data):
        response = client.put(
            "/api/recipes/missing-id",
            json=sample_recipe_data,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"

    def test_delete_recipe(self, client, clean_storage, sample_recipe_data):
        create_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = create_response.json()["id"]

        delete_response = client.delete(f"/api/recipes/{recipe_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["message"] == "Recipe deleted successfully"
        assert client.get(f"/api/recipes/{recipe_id}").status_code == 404

    def test_delete_recipe_not_found(self, client, clean_storage):
        response = client.delete("/api/recipes/missing-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "Recipe not found"


class TestValidationErrors:
    def test_create_recipe_missing_required_field_returns_422(
        self, client, clean_storage
    ):
        response = client.post("/api/recipes", json={"title": "Only Title"})
        assert response.status_code == 422
        assert "detail" in response.json()

    def test_create_recipe_invalid_difficulty_returns_422(
        self, client, clean_storage, sample_recipe_data
    ):
        payload = {**sample_recipe_data, "difficulty": "Impossible"}
        response = client.post("/api/recipes", json=payload)
        assert response.status_code == 422

    def test_create_recipe_empty_ingredients_returns_422(
        self, client, clean_storage, sample_recipe_data
    ):
        payload = {**sample_recipe_data, "ingredients": []}
        response = client.post("/api/recipes", json=payload)
        assert response.status_code == 422

    def test_create_recipe_blank_title_returns_422(
        self, client, clean_storage, sample_recipe_data
    ):
        payload = {**sample_recipe_data, "title": "   "}
        response = client.post("/api/recipes", json=payload)
        assert response.status_code == 422

    def test_create_recipe_title_too_long_returns_422(
        self, client, clean_storage, sample_recipe_data
    ):
        payload = {**sample_recipe_data, "title": "x" * 201}
        response = client.post("/api/recipes", json=payload)
        assert response.status_code == 422

    def test_update_recipe_invalid_payload_returns_422(
        self, client, clean_storage, sample_recipe_data
    ):
        create_response = client.post("/api/recipes", json=sample_recipe_data)
        recipe_id = create_response.json()["id"]

        response = client.put(
            f"/api/recipes/{recipe_id}",
            json={**sample_recipe_data, "ingredients": []},
        )
        assert response.status_code == 422


class TestExportAndImport:
    def test_export_recipes(self, client, clean_storage, sample_recipe_data):
        client.post("/api/recipes", json=sample_recipe_data)

        response = client.get("/api/recipes/export")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["title"] == sample_recipe_data["title"]

    def test_import_valid_recipes(self, client, clean_storage, sample_recipe_data):
        payload = json.dumps([sample_recipe_data]).encode("utf-8")
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.json", BytesIO(payload), "application/json")},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert "Successfully imported" in body["message"]

    def test_import_invalid_json_returns_400(self, client, clean_storage):
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.json", BytesIO(b"{bad json"), "application/json")},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid JSON format"

    def test_import_non_array_returns_400(self, client, clean_storage):
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.json", BytesIO(b'{"title": "Nope"}'), "application/json")},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "JSON must be an array of recipes"

    def test_import_empty_array_returns_400(self, client, clean_storage):
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.json", BytesIO(b"[]"), "application/json")},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "JSON array must contain at least one recipe"

    def test_import_file_too_large_returns_400(self, client, clean_storage):
        large_payload = b"[" + b" " * 1_000_001 + b"]"
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.json", BytesIO(large_payload), "application/json")},
        )
        assert response.status_code == 400
        assert "File too large" in response.json()["detail"]

    def test_import_invalid_recipes_returns_400(self, client, clean_storage):
        response = client.post(
            "/api/recipes/import",
            files={
                "file": (
                    "recipes.json",
                    BytesIO(b'[{"title": "Missing fields"}]'),
                    "application/json",
                )
            },
        )
        assert response.status_code == 400
        assert "No valid recipes found" in response.json()["detail"]

    def test_import_non_json_extension_returns_400(self, client, clean_storage):
        response = client.post(
            "/api/recipes/import",
            files={"file": ("recipes.txt", BytesIO(b"[]"), "text/plain")},
        )
        assert response.status_code == 400
        assert "JSON file" in response.json()["detail"]


class TestSchemaValidationScript:
    def test_sample_recipes_pass_schema_validation(self):
        valid_count, errors = validate_recipe_file(PROJECT_ROOT / "sample-recipes.json")
        assert valid_count == 3
        assert errors == []

    def test_invalid_recipe_file_fails_validation(self, tmp_path):
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text('[{"title": "Only title"}]', encoding="utf-8")

        valid_count, errors = validate_recipe_file(invalid_file)
        assert valid_count == 0
        assert len(errors) == 1
